import logging
import suds
from django.db import models
from django.db.models import Q

from djnetaxept.utils import get_client, get_basic_registerrequest, get_netaxept_object, handle_response_exception
from djnetaxept.operations import register, process, query, batch
from djnetaxept.exceptions import PaymentNotAuthorized, AmountAllreadyCaptured, NoAmountCaptured, ProcessException

logger = logging.getLogger('djnetaxept.managers')

class NetaxeptPaymentManager(models.Manager):

    def register_payment(self,
        redirect_url=None,
        amount=None,
        currencycode=None,
        ordernumber=None,
        description=None,
        language=None):

        client = get_client()
        request = get_basic_registerrequest(client, redirect_url, language)

        order = get_netaxept_object(client, 'Order')
        order.Amount = amount # store
        order.CurrencyCode = currencycode # store
        order.OrderNumber = ordernumber# store
        order.UpdateStoredPaymentInfo = None

        request.Order = order
        request.Description = description # Store

        payment = self.model(
             amount=amount,
             currencycode=currencycode,
             ordernumber=ordernumber,
             description=description
        )

        try:
            response = register(client, request)
            payment.transaction_id = response.TransactionId
        except suds.WebFault as e:
            logger.error("Error registering payment")
            handle_response_exception(e, payment)
        finally:
            payment.save()

        return payment


class NetaxeptRecurringPaymentManager(models.Manager):
    def register_recurring_payment(self,
        redirect_url=None,
        amount=None,
        currencycode=None,
        ordernumber=None,
        description=None,
        language=None,
        recurring_type=None,
        freq=None,
        expiry_date=None):

        client = get_client()
        request = get_basic_registerrequest(client, redirect_url, language)

        order = get_netaxept_object(client, 'Order')
        order.Amount = amount # store
        order.CurrencyCode = currencycode # store
        order.OrderNumber = ordernumber# store
        order.UpdateStoredPaymentInfo = True

        request.Order = order
        request.Description = description # Store

        request.Recurring = get_netaxept_object(client, 'Recurring')
        request.Recurring.Type = recurring_type
        request.Recurring.Frequency = freq
        request.Recurring.ExpiryDate = int(expiry_date.strftime('%Y%m%d'))

        payment = self.model(
             amount=amount,
             currencycode=currencycode,
             ordernumber=ordernumber,
             description=description,
             recurring_type=recurring_type,
             minimum_frequency=freq,
             expiry_date=expiry_date
        )

        try:
            response = register(client, request)
            payment.transaction_id = response.TransactionId
        except suds.WebFault as e:
            logger.error("Error registering payment")
            handle_response_exception(e, payment)
        finally:
            payment.save()

        return payment


class NetaxeptTransactionManager(models.Manager):

    def auth_payment(self, payment):

        if not payment.completed():
             logger.error("Payment registration not completed")
             raise PaymentRegistrationNotCompleted

        client = get_client()
        operation = 'AUTH'

        request = get_netaxept_object(client, 'ProcessRequest')
        request.Operation = operation
        request.TransactionId = payment.transaction_id

        transaction = self.model(
            payment=payment,
            transaction_id=payment.transaction_id,
            operation=operation
        )

        try:
            response = process(client, request)
        except suds.WebFault as e:
            logger.error("Authorization on payment failed")
            handle_response_exception(e, transaction)
        finally:
            transaction.save()

        return transaction

    def sale_payment(self, payment):

        if not payment.completed():
            logger.error("Payment registration not completed")
            raise PaymentRegistrationNotCompleted

        client = get_client()
        operation = 'SALE'

        request = get_netaxept_object(client, 'ProcessRequest')
        request.Operation = operation
        request.TransactionId = payment.transaction_id

        transaction = self.model(
            payment=payment,
            transaction_id=payment.transaction_id,
            operation=operation
        )

        try:
            response = process(client, request)
        except suds.WebFault as e:
            logger.error("Sale on payment failed")
            handle_response_exception(e, transaction)
        finally:
            transaction.save()

        return transaction

    def capture_payment(self, payment, amount):

        self.require_auth(payment)

        client = get_client()
        operation = 'CAPTURE'

        request = get_netaxept_object(client, 'ProcessRequest')
        request.Operation = operation
        request.TransactionId = payment.transaction_id
        request.TransactionAmount = amount

        transaction = self.model(
            payment=payment,
            transaction_id=payment.transaction_id,
            amount=amount,
            operation=operation
        )

        try:
            response = process(client, request)
        except suds.WebFault as e:
            logger.error("Capture on payment not failed")
            handle_response_exception(e, transaction)
        finally:
            transaction.save()

        return transaction

    def credit_payment(self, payment, amount):

        if not self.get_query_set().filter(Q(operation='CAPTURE') | Q(operation='SALE'), payment=payment).exists():
            logger.error("No amount captured, cannot credit")
            raise NoAmountCaptured

        client = get_client()
        operation = 'CREDIT'

        request = get_netaxept_object(client, 'ProcessRequest')
        request.Operation = operation
        request.TransactionId = payment.transaction_id
        request.TransactionAmount = amount

        transaction = self.model(
            payment=payment,
            transaction_id=payment.transaction_id,
            amount=amount,
            operation=operation
        )

        try:
            response = process(client, request)
        except suds.WebFault as e:
            logger.error("Credit on payment failed")
            handle_response_exception(e, transaction)
        finally:
            transaction.save()

        return transaction

    def annul_payment(self, payment):

        self.require_auth(payment)

        if self.get_query_set().filter(Q(operation='CAPTURE') | Q(operation='SALE'), payment=payment).exists():
            logger.error("Amount allready captured, cannot annul")
            raise AmountAllreadyCaptured

        client = get_client()
        operation = 'ANNUL'

        request = get_netaxept_object(client, 'ProcessRequest')
        request.Operation = operation
        request.TransactionId = payment.transaction_id

        transaction = self.model(
            payment=payment,
            transaction_id=payment.transaction_id,
            operation=operation
        )

        try:
            response = process(client, request)
        except suds.WebFault as e:
            logger.error("Annul on payment failed")
            handle_response_exception(e, transaction)
        finally:
            transaction.save()

        return transaction

    def require_auth(self, payment):
        if not self.get_query_set().filter(payment=payment, operation='AUTH').exists():
            logger.error("Payment not authorized")
            raise PaymentNotAuthorized

    def verify_payment(self, payment):
        if not payment.completed():
             logger.error("Payment registration not completed")
             raise PaymentRegistrationNotCompleted

        client = get_client()
        operation = 'VERIFY'

        request = get_netaxept_object(client, 'ProcessRequest')
        request.Operation = operation
        request.TransactionId = payment.transaction_id

        transaction = self.model(
            payment=payment,
            transaction_id=payment.transaction_id,
            operation=operation
        )

        try:
            response = process(client, request)
        except suds.WebFault as e:
            logger.error("Authorization on payment failed")
            handle_response_exception(e, transaction)
        finally:
            transaction.save()

