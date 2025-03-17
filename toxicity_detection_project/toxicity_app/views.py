from django.shortcuts import render

# Create your views here.
from django.shortcuts import render

def index(request):
    return render(request, 'toxicity_app/index.html')

def chat_room(request):
    username = request.POST.get('username', 'Anonymous')
    room_name = 'lobby'  # Using a default room for simplicity
    return render(request, 'toxicity_app/chat_room.html', {
        'room_name': room_name,
        'username': username
    })