from django.contrib import admin
from djnetaxept.models import NetaxeptPayment, NetaxeptRecurringPayment, NetaxeptTransaction

admin.site.register(NetaxeptPayment)
admin.site.register(NetaxeptRecurringPayment)
admin.site.register(NetaxeptTransaction)
