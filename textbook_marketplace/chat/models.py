from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

User = get_user_model()


class Message(models.Model):
    """ Model for messages in user chats. """
    sender = models.ForeignKey(User,
                               related_name='message_sender',
                               on_delete=models.SET(AnonymousUser.id))
    recipient = models.ForeignKey(User,
                                  related_name='message_recipient',
                                  on_delete=models.SET(AnonymousUser.id))
    text = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sender', 'recipient']

    def __str__(self):
        return (f'Sender: {self.sender.username}; '
                f'Recipient: {self.recipient.username}; '
                f'Text: {self.text[:15]}')
