# core/views.py
from django.shortcuts import render
from .models import InfoSection
from .forms import DataDeletionRequestForm
from django.contrib import messages
from django.shortcuts import redirect


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import InfoSectionSerializer, DataDeletionRequestSerializer

def legal_page(request):
    sections = InfoSection.objects.filter(page='legal', is_active=True)
    return render(request, 'pages/legal.html', {'sections': sections})


def support_safety_page(request):
    sections = InfoSection.objects.filter(page='support', is_active=True)
    return render(request, 'pages/support_safety.html', {'sections': sections})


def legal_page_user(request):
    sections = InfoSection.objects.filter(page='legal_user', is_active=True)
    return render(request, 'pages/legal_user.html', {'sections': sections})


def support_safety_page_user(request):
    sections = InfoSection.objects.filter(page='support_user', is_active=True)
    return render(request, 'pages/support_safety_user.html', {'sections': sections})



def privacy_policy(request):
    sections = InfoSection.objects.filter(page='privacy', is_active=True)
    return render(request, 'pages/privacy_policy.html', {
        'sections': sections,
        'page_title': 'Privacy Policy'
    })

def data_usage_overview(request):
    sections = InfoSection.objects.filter(page='data_usage', is_active=True)
    return render(request, 'pages/data_usage.html', {
        'sections': sections,
        'page_title': 'Data Usage Overview'
    })

def request_data_deletion(request):
    if request.method == 'POST':
        form = DataDeletionRequestForm(request.POST)
        if form.is_valid():
            deletion_request = form.save(commit=False)
            if request.user.is_authenticated:
                deletion_request.user = request.user
            deletion_request.save()
            messages.success(request, "Your data deletion request has been submitted. We'll process it soon.")
            # Redirect back to the same page so the user sees the success state
            return redirect('request_data_deletion')
    else:
        form = DataDeletionRequestForm()

    return render(request, 'pages/request_data_deletion.html', {
        'form': form,
        'page_title': 'Request Data Deletion'
    })

class DataDeletionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Fetch content for the Data Deletion Request page.
        """
        sections = InfoSection.objects.filter(page='deletion_request', is_active=True).order_by('order')
        serializer = InfoSectionSerializer(sections, many=True)
        return Response({
            "status": 200,
            "success": True,
            "message": "Data deletion page content fetched successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Submit a data deletion request.
        """
        serializer = DataDeletionRequestSerializer(data=request.data)
        if serializer.is_valid():
            extra_data = {}
            if request.user.is_authenticated:
                extra_data['user'] = request.user
            
            deletion_request = serializer.save(**extra_data)
            
            return Response({
                "status": 201,
                "success": True,
                "message": "Your data deletion request has been submitted successfully.",
                "data": DataDeletionRequestSerializer(deletion_request).data
            }, status=status.HTTP_201_CREATED)

        
        return Response({
            "status": 400,
            "success": False,
            "message": "Invalid data submitted.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

