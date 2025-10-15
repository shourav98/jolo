# urls.py
from django.urls import path
from .views import (
    ChatSessionsAPIView,
    StartChatAPIView,    
    MessagesAPIView,
    SendPriorityMessageAPIView,    
    AddReactionAPIView,
    OnlineCreatorsAPIView,    
    UpdateUserStatusAPIView,
    WelcomeMessageSettingsAPIView,
    CheckFreeWindowAPIView,
)

urlpatterns = [
    path('chats/', ChatSessionsAPIView.as_view(), name='chat-sessions'),
    path('chats/start/<uuid:creator_id>/', StartChatAPIView.as_view(), name='start-chat'),
    path('chats/<uuid:session_id>/messages/', MessagesAPIView.as_view(), name='chat-messages'),
    path('chats/<uuid:session_id>/priority/', SendPriorityMessageAPIView.as_view(), name='priority-message'),
    path('messages/<uuid:message_id>/reaction/', AddReactionAPIView.as_view(), name='add-reaction'),
    path('creators/online/', OnlineCreatorsAPIView.as_view(), name='online-creators'),
    path('user/status/', UpdateUserStatusAPIView.as_view(), name='update-status'),
    path('settings/welcome-message/', WelcomeMessageSettingsAPIView.as_view(), name='welcome-settings'),
    path('chats/<uuid:session_id>/free-window/', CheckFreeWindowAPIView.as_view(), name='check-free-window'),
]