from django.urls import path
from .views import (
    ChatSearchAPIView,
    ChatSessionsAPIView,
    StartChatAPIView,    
    MessagesAPIView,
    SendPriorityMessageAPIView,    
    AddReactionAPIView,
    OnlineCreatorsAPIView,    
    UpdateUserStatusAPIView,
    CheckFreeWindowAPIView,
    DeleteMessageAPIView,
    TranslateMessageAPIView,
    AllwisperMessagesAPIView,
    ChatSessionMessagesAPIView,

)

urlpatterns = [
    path('chats/search/', ChatSearchAPIView.as_view(), name='chat-search'),
    path('chats/', ChatSessionsAPIView.as_view(), name='chat-sessions'),
    path('chats/start/<int:user_id>/', StartChatAPIView.as_view(), name='start-chat'),  # user IDs are integers
    path('chats/<uuid:session_id>/messages/', MessagesAPIView.as_view(), name='chat-messages'),
    path('chats/<uuid:session_id>/priority/', SendPriorityMessageAPIView.as_view(), name='priority-message'),
    path('messages/<uuid:message_id>/reaction/', AddReactionAPIView.as_view(), name='add-reaction'),
    path('messages/<uuid:message_id>/delete/', DeleteMessageAPIView.as_view(), name='delete-message'),
    path('creators/online/', OnlineCreatorsAPIView.as_view(), name='online-creators'),
    path('user/status/', UpdateUserStatusAPIView.as_view(), name='update-status'),
    path('chats/<uuid:session_id>/free-window/', CheckFreeWindowAPIView.as_view(), name='check-free-window'),
    path('messages/<uuid:message_id>/translate/', TranslateMessageAPIView.as_view(), name='translate-message'),
    path('allwisper/messages/', AllwisperMessagesAPIView.as_view(), name='allwisper-messages'),

    path('chat-sessions/<uuid:session_id>/all-messages/', ChatSessionMessagesAPIView.as_view(), name='chat-session-messages'),
]