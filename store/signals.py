from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, Notification




@receiver(post_save, sender='store.Order')
def send_order_status_notifications(sender, instance, created, **kwargs):
    user = instance.user
    devices = FCMDevice.objects.filter(user=user, active=True)

    if not devices.exists():
        return


    status_messages = {
        'Accepted': {
            'title': "Order Confirmed! 🎉",
            'body': f"Your payment for Order #{instance.id} was successful. We're getting it ready!"
        },
        'Shipped': {
            'title': "On its way! 🚚",
            'body': f"Your Order #{instance.id} has been shipped and is heading your way."
        },
        'Delivered': {
            'title': "Package Delivered! 📦",
            'body': f"Order #{instance.id} has been delivered. Enjoy your purchase!"
        },
        'Cancelled': {
            'title': "Order Cancelled",
            'body': f"Order #{instance.id} has been cancelled. If this was a mistake, please contact support."
        }
    }

    message_data = status_messages.get(instance.status.lower())

    if message_data:
        for device in devices:
            try:
                device.send_message(
                    Message(
                        notification=Notification(
                            title=message_data['title'],
                            body=message_data['body']
                        )
                    )
                )
            except Exception as e:
                print(f"Error sending {instance.status} notification: {e}")