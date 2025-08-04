from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import json
from math import radians, sin, cos, sqrt, atan2
from collections import defaultdict, deque

# ---------------- Gemini API ----------------
API_KEY = 'AIzaSyD0QBoMd4P_bGRqk1JNsVfxYqCdZtXQYs0'
API_URL = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}'

# ----------------- Graph-based Routing -----------------
def build_graph(routes):
    graph = defaultdict(list)
    for (src, dst), stops in routes.items():
        all_nodes = [src] + stops + [dst]
        for i in range(len(all_nodes) - 1):
            u, v = all_nodes[i].lower(), all_nodes[i + 1].lower()
            graph[u].append(v)
            graph[v].append(u)
    return graph

def find_path(graph, start, end):
    start, end = start.lower(), end.lower()
    queue = deque([[start]])
    visited = set()
    while queue:
        path = queue.popleft()
        node = path[-1]
        if node == end:
            return path
        if node not in visited:
            visited.add(node)
            for neighbor in graph[node]:
                if neighbor not in visited:
                    queue.append(path + [neighbor])
    return None

@csrf_exempt
def get_response(request):
    if request.method == 'POST':
        message = request.POST.get('message', '').lower().strip()

        if message == "stop":
            return JsonResponse({'response': "Voice assistant stopped."})

        stage = request.session.get('chat_stage', 'initial')

        if stage == 'initial':
            if 'distance' in request.session and 'costs' in request.session:
                source = request.session.get('source', '').title()
                destination = request.session.get('destination', '').title()
                distance = request.session.get('distance')
                costs = request.session.get('costs')
                low_meal = request.session.get('low_meal', {})
                med_meal = request.session.get('med_meal', {})
                high_meal = request.session.get('high_meal', {})

                low_food = ', '.join([f"{item} ₹{cost}" for item, cost in low_meal.items()])
                med_food = ', '.join([f"{item} ₹{cost}" for item, cost in med_meal.items()])
                high_food = ', '.join([f"{item} ₹{cost}" for item, cost in high_meal.items()])

                response = (
                    f"The distance between {source} and {destination} is {distance} kilometers.\n"
                    f"Travel costs: Bus ₹{costs['bus']}, Train ₹{costs['train']}, Flight ₹{costs['flight']}.\n"
                    f"\nLow Budget Food: {low_food}\n"
                    f"Medium Budget Food: {med_food}\n"
                    f"High Budget Food: {high_food}\n"
                    f"\nWould you like to book a ticket or ask any questions?"
                )
                request.session['chat_stage'] = 'ask_action'
                return JsonResponse({'response': response})

        elif stage == 'ask_action':
            if "book" in message:
                request.session['chat_stage'] = 'ask_name'
                return JsonResponse({'response': "Please enter your name to proceed with booking."})
            else:
                prompt = f"Answer this user query: {message}"
                r = requests.post(API_URL, json={"contents": [{"parts": [{"text": prompt}]}]})
                if r.status_code == 200:
                    try:
                        text = r.json()['candidates'][0]['content']['parts'][0]['text']
                        return JsonResponse({'response': text})
                    except Exception as e:
                        return JsonResponse({'response': f"Error parsing AI response: {str(e)}"})

        elif stage == 'ask_name':
            name = message.title()
            ticket = {
                'name': name,
                'source': request.session.get('source'),
                'destination': request.session.get('destination'),
                'mode': 'train',
                'distance': request.session.get('distance'),
                'cost': request.session.get('costs', {}).get('train'),
                'travel_date': request.session.get('travel_date'),
                'full_path': request.session.get('path', [])
            }
            request.session['ticket'] = ticket
            request.session['chat_stage'] = 'download'
            return JsonResponse({'response': f"Ticket booked for {name}. Say 'download ticket' to get your ticket."})

        elif stage == 'download':
            if "download" in message:
                ticket = request.session.get('ticket')
                if ticket:
                    path = request.session.get('path', [])
                    full_path = f"{ticket['source'].title()} → " + " → ".join(path) + f" → {ticket['destination'].title()}"
                    txt = (
                        f"----- Travel Ticket -----\n"
                        f"Passenger: {ticket['name']}\n"
                        f"Mode: {ticket['mode']}\n"
                        f"From: {ticket['source'].title()}\n"
                        f"To: {ticket['destination'].title()}\n"
                        f"Date: {ticket['travel_date']}\n"
                        f"Distance: {ticket['distance']} km\n"
                        f"Cost: ₹{ticket['cost']}\n"
                        f"Path: {full_path}\n"
                        f"-------------------------\n"
                    )
                    request.session['chat_stage'] = 'final_qa'
                    return JsonResponse({'response': txt + "\nThanks for booking. Happy journey!\nDo you have any other questions?"})

        elif stage == 'final_qa':
            if message in ["no", "no thanks", "exit"]:
                request.session['chat_stage'] = 'initial'
                return JsonResponse({'response': "Goodbye!"})
            else:
                prompt = f"Answer this user query: {message}"
                r = requests.post(API_URL, json={"contents": [{"parts": [{"text": prompt}]}]})
                if r.status_code == 200:
                    try:
                        text = r.json()['candidates'][0]['content']['parts'][0]['text']
                        return JsonResponse({'response': text + "\nDo you have any other questions?"})
                    except Exception as e:
                        return JsonResponse({'response': f"Error parsing AI response: {str(e)}"})

        return JsonResponse({'response': 'Sorry, I could not process your request.'})

    return JsonResponse({'response': 'Invalid method'})

# ---------------- Coordinates ----------------
city_coords = {
    "delhi": (28.6139, 77.2090),
    "agra": (27.1767, 78.0081),
    "jaipur": (26.9124, 75.7873),
    "udaipur": (24.5854, 73.7125),
    "nashik": (19.9975, 73.7898),
    "mumbai": (19.0760, 72.8777),
    "hyderabad": (17.3850, 78.4867),
    "bangalore": (12.9716, 77.5946),
    "chennai": (13.0827, 80.2707),
    "kolkata": (22.5726, 88.3639),
    "lucknow": (26.8467, 80.9462),
    "pune": (18.5204, 73.8567),
    "kanpur": (26.4499, 80.3319),
    "varanasi": (25.3176, 82.9739),
    "asansol": (23.6739, 86.9524),
    "bhubaneswar": (20.2961, 85.8245),
    "indore": (22.7196, 75.8577),
    "bhopal": (23.2599, 77.4126),
    "nagpur": (21.1458, 79.0882),
    "kurnool": (15.8281, 78.0373),
    "gwalior": (26.2183, 78.1828),
    "patna": (25.5941, 85.1376),
    "ranchi": (23.3441, 85.3096),
    "guntur": (16.3067, 80.4365),
    "palnadu": (16.5253, 79.9674),
    
    # More cities in Andhra Pradesh
    "vijayawada": (16.5062, 80.6480),
    "visakhapatnam": (17.6868, 83.2185),
    "tirupati": (13.6288, 79.4192),
    "nellore": (14.4426, 79.9865),
    "kadapa": (14.4674, 78.8241),
    "kakinada": (16.9891, 82.2475),
    "ongole": (15.5057, 80.0499),
    "eluru": (16.7107, 81.0952),
    "anantapur": (14.6819, 77.6006),
    "sattenapalli": (16.3942, 80.1514),
    "nalgonda": (17.0541, 79.2671),
    "tenali": (16.2430, 80.6400),
    "machilipatnam": (16.1875, 81.1389),
    "narasaraopet": (16.2340, 80.0499),
    "chirala": (15.8246, 80.3522),
    "tadepalligudem": (16.8130, 81.5271),
    "bapatla": (15.9049, 80.4675),
    "proddatur": (14.7502, 78.5481),
    "markapur": (15.7352, 79.2708),
    "sriharikota": (13.7195, 80.2305),
    "vizianagaram": (18.1169, 83.4115),
    "srikakulam": (18.2969, 83.8973),
    "parvathipuram": (18.7830, 83.4265),
    "mandapeta": (16.8707, 81.9290),
    "amalapuram": (16.5788, 82.0061),
    "repalle": (16.0187, 80.8290),
    "peddapuram": (17.0786, 82.1391),
    "gudivada": (16.4329, 80.9963),
    "nandyal": (15.4882, 78.4864),
    "rayachoti": (14.0567, 78.7519),
    "hindupur": (13.8291, 77.4927),


    "surat": (21.1702, 72.8311),
    "ahmedabad": (23.0225, 72.5714),
    "rajkot": (22.3039, 70.8022),
    "amritsar": (31.6340, 74.8723),
    "ludhiana": (30.9000, 75.8573),
    "chandigarh": (30.7333, 76.7794),
    "jammu": (32.7266, 74.8570),
    "guwahati": (26.1445, 91.7362),
    "shillong": (25.5788, 91.8933),
    "coimbatore": (11.0168, 76.9558),
    "madurai": (9.9252, 78.1198),
    "kochi": (9.9312, 76.2673),
    "trivandrum": (8.5241, 76.9366),
    "mysore": (12.2958, 76.6394),
    "hubli": (15.3647, 75.1240),
    "aurangabad": (19.8762, 75.3433),
    "jamshedpur": (22.8046, 86.2029),
    "raipur": (21.2514, 81.6296),
    "vishakhapatnam": (17.6868, 83.2185),
}




# ---------------- Routes between cities ----------------
routes = {
    ('delhi', 'kolkata'): ['kanpur', 'varanasi', 'asansol'],
    ('delhi', 'mumbai'): ['jaipur', 'udaipur', 'nashik'],
    ('bangalore', 'hyderabad'): ['kurnool'],
    ('chennai', 'kolkata'): ['bhubaneswar'],
    ('delhi', 'pune'): ['jaipur', 'indore'],
    ('delhi', 'hyderabad'): ['agra', 'nagpur'],
    ('mumbai', 'kolkata'): ['nagpur', 'raipur', 'ranchi'],
    ('lucknow', 'mumbai'): ['jhansi', 'bhopal', 'nashik'],
    ('bangalore', 'mumbai'): ['hubli', 'pune'],
    ('delhi', 'chennai'): ['gwalior', 'nagpur', 'hyderabad'],
    ('kolkata', 'chennai'): ['bhubaneswar', 'visakhapatnam'],
    ('agra', 'pune'): ['indore', 'aurangabad'],
    ('guntur', 'hyderabad'): ['nalgonda'],
    ('palnadu', 'guntur'): ['sattenapalli'],

    # Andhra Pradesh routes
    ('vijayawada', 'guntur'): ['tenali'],
    ('guntur', 'nellore'): ['ongole'],
    ('tirupati', 'kadapa'): ['rayachoti'],
    ('guntur', 'visakhapatnam'): ['vijayawada', 'rajahmundry', 'kakinada'],
    ('vijayawada', 'tirupati'): ['nellore'],
    ('tirupati', 'chennai'): ['sriharikota'],
    ('visakhapatnam', 'srikakulam'): ['vizianagaram'],
    ('guntur', 'eluru'): ['vijayawada'],
    ('eluru', 'kakinada'): ['mandapeta'],
    ('nandyal', 'kurnool'): ['nalgonda'],
    ('markapur', 'kadapa'): ['proddatur'],
    ('machilipatnam', 'guntur'): ['repalle'],
    ('bapatla', 'guntur'): ['chirala'],
    ('vijayawada', 'raipur'): ['nagpur'],

    # Other regions
    ('coimbatore', 'bangalore'): ['mysore'],
    ('amritsar', 'delhi'): ['ludhiana', 'chandigarh'],
    ('jammu', 'delhi'): ['amritsar'],
    ('guwahati', 'kolkata'): ['shillong'],
    ('pune', 'hyderabad'): ['solapur'],
    ('mumbai', 'surat'): ['ahmedabad'],
    ('bhopal', 'nagpur'): ['betul'],
    ('ranchi', 'patna'): ['gaya'],
    ('jamshedpur', 'kolkata'): ['kharagpur']
}
routes.update({
    # Gujarat
    ('mumbai', 'ahmedabad'): ['surat'],
    ('ahmedabad', 'rajkot'): ['limdi'],
    ('ahmedabad', 'delhi'): ['udaipur', 'jaipur'],
    
    # Punjab / North
    ('delhi', 'amritsar'): ['panipat', 'ludhiana'],
    ('delhi', 'jammu'): ['panipat', 'ludhiana', 'amritsar', 'pathankot'],
    ('delhi', 'chandigarh'): ['panipat', 'ambala'],
    ('chandigarh', 'amritsar'): ['jalandhar', 'ludhiana'],

    # North East
    ('kolkata', 'guwahati'): ['bardhaman', 'malda', 'siliguri'],
    ('guwahati', 'shillong'): ['nagaon'],

    # South - Tamil Nadu and Kerala
    ('bangalore', 'coimbatore'): ['mysore'],
    ('coimbatore', 'madurai'): ['dindigul'],
    ('madurai', 'trivandrum'): ['tirunelveli', 'nagercoil'],
    ('kochi', 'trivandrum'): ['alleppey'],
    ('bangalore', 'trivandrum'): ['salem', 'madurai'],

    # Karnataka / Maharashtra
    ('bangalore', 'hubli'): ['davangere'],
    ('hubli', 'mumbai'): ['kolhapur', 'pune'],
    ('aurangabad', 'pune'): ['ahmednagar'],
    ('aurangabad', 'nagpur'): ['akola', 'amravati'],

    # Central / East India
    ('nagpur', 'raipur'): ['bhilai', 'durg'],
    ('raipur', 'jamshedpur'): ['ranchi'],
    ('jamshedpur', 'kolkata'): ['kharagpur'],

    # Andhra Pradesh + Correct Paths
    ('vijayawada', 'visakhapatnam'): ['eluru', 'rajahmundry'],
    ('visakhapatnam', 'srikakulam'): ['vizianagaram'],
    ('guntur', 'visakhapatnam'): ['vijayawada'],
    ('guntur', 'tirupati'): ['ongole', 'nellore'],
    ('guntur', 'anantapur'): ['kurnool'],
    ('tirupati', 'chennai'): ['sriharikota'],
    ('nellore', 'chennai'): ['sriharikota'],
    ('kurnool', 'hyderabad'): ['nalgonda'],
})

# ---------------- Auth Views ----------------

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('trip_input')
    else:
        form = UserCreationForm()
    return render(request, 'smart_traverser/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('trip_input')
    else:
        form = AuthenticationForm()
    return render(request, 'smart_traverser/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

# ---------------- Trip Flow ----------------
@login_required
def trip_input_view(request):
    if request.method == 'POST':
        source = request.POST.get('source').lower()
        destination = request.POST.get('destination').lower()
        travel_date = request.POST.get('travel_date')

        if source not in city_coords or destination not in city_coords:
            return render(request, 'smart_traverser/trip_input.html', {'error': 'Invalid city name.'})

        request.session.update({
            'source': source,
            'destination': destination,
            'travel_date': travel_date
        })
        return redirect('budget_detail')
    return render(request, 'smart_traverser/trip_input.html')

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from math import radians, sin, cos, sqrt, atan2


@login_required
def budget_detail_view(request):
    src = request.session.get('source')
    dst = request.session.get('destination')
    travel_date = request.session.get('travel_date')

    if not src or not dst:
        return redirect('trip_input')

 
    else:
        def haversine(a, b):
            R = 6371
            lat1, lon1 = radians(a[0]), radians(a[1])
            lat2, lon2 = radians(b[0]), radians(b[1])
            dlat, dlon = lat2 - lat1, lon2 - lon1
            t = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
            return round(2 * atan2(sqrt(t), sqrt(1 - t)) * R, 2)

        distance = haversine(city_coords[src], city_coords[dst])
        costs = {
            'bus': round(distance * 5, 2),
            'train': round(distance * 3, 2),
            'flight': round(distance * 10, 2)
        }
        no_flight_list = ['guntur', 'palnadu', 'sattenapalli', 'kanpur']
        if src in no_flight_list or dst in no_flight_list:
             costs['flight'] = 0.0
    # --- Route Path Display ---
        # --- Route Path Display Using Graph ---
    graph = build_graph(routes)
    path = find_path(graph, src, dst)

    if path:
        full_path = [city.title() for city in path]
    else:
        full_path = [src.title(), dst.title()]


    # --- Food Costs based on distance ---
    low_meal = {
        "Veg Meal": 50 + int(distance * 0.1),
        "Snacks": 30,
        "Tea/Coffee": 20,
        "Fruit Pack": 25
    }
    med_meal = {
        "Veg/Non-Veg Meal": 100 + int(distance * 0.15),
        "Juice": 50,
        "Sandwich": 60,
        "Biscuits": 20
    }
    high_meal = {
        "Premium Meal": 200 + int(distance * 0.2),
        "Drinks": 100,
        "Dessert": 80,
        "Luxury Snacks": 100
    }

    # --- Save to Session ---
    request.session['distance'] = distance
    request.session['costs'] = costs
    request.session['path'] = full_path

    # --- Render Output ---
    return render(request, 'smart_traverser/budget_detail.html', {
        'source': src.title(),
        'destination': dst.title(),
        'distance': distance,
        'travel_date': travel_date,
        'bus_cost': costs['bus'],
        'train_cost': costs['train'],
        'flight_cost': costs['flight'],
        'path': full_path,
        'low_meal': low_meal,
        'med_meal': med_meal,
        'high_meal': high_meal
    })


@login_required
def budget_options_view(request):
    source = request.session.get('source')
    destination = request.session.get('destination')
    distance = request.session.get('distance')
    costs = request.session.get('costs', {})
    path = request.session.get('path', [])

    return render(request, 'smart_traverser/budget_detail.html', {
        'source': source.title() if source else '',
        'destination': destination.title() if destination else '',
        'distance': distance,
        'bus_cost': costs.get('bus'),
        'train_cost': costs.get('train'),
        'flight_cost': costs.get('flight'),
        'path': path or [" "]
    })




@login_required
def book_ticket_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        source = request.POST.get('source')
        destination = request.POST.get('destination')
        mode = request.POST.get('mode')

        # Get full path (both direct and reverse supported)
        graph = build_graph(routes)
        path = find_path(graph, source, destination)

        if path:
           full_path = [city.title() for city in path]
        else:
           full_path = [source.title(), destination.title()]


        # Build ticket info
        ticket = {
            'name': name,
            'source': source,
            'destination': destination,
            'mode': mode,
            'distance': request.session.get('distance'),
            'cost': request.session.get('costs', {}).get(mode.lower()),
            'travel_date': request.session.get('travel_date'),
            'full_path': full_path
        }

        request.session['ticket'] = ticket
        return render(request, 'smart_traverser/ticket.html', ticket)

    return redirect('trip_input')

@login_required
def download_ticket_view(request):
    ticket = request.session.get('ticket')
    if not ticket:
        return redirect('trip_input')

    path = request.session.get('path', 'Direct route')
    if isinstance(path, list):
        full_path = f"{ticket['source'].title()} → " + " → ".join(path) + f" → {ticket['destination'].title()}"
    else:
        full_path = path

    txt = (
        f"----- Travel Ticket -----\n"
        f"Passenger: {ticket['name']}\n"
        f"Mode: {ticket['mode']}\n"
        f"From: {ticket['source'].title()}\n"
        f"To: {ticket['destination'].title()}\n"
        f"Date: {ticket['travel_date']}\n"
        f"Distance: {ticket['distance']} km\n"
        f"Cost: ₹{ticket['cost']}\n"
        f"Path: {full_path}\n"
        f"-------------------------\n"
    )
    resp = HttpResponse(txt, content_type='text/plain')
    resp['Content-Disposition'] = 'attachment; filename="ticket.txt"'
    return resp
