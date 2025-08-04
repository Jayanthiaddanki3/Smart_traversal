from django import forms

class TravelForm(forms.Form):
    travel_file = forms.FileField(required=True, label="Upload Travel Plan")
    budget = forms.DecimalField(label="Enter Budget (INR)", decimal_places=2, max_digits=10)
