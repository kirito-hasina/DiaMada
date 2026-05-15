from django.contrib import admin

# Register your models here.
from .models import User, Passager, Agent, Chauffeur, AdminProfil

admin.site.register(User)
admin.site.register(Passager)
admin.site.register(Agent)
admin.site.register(Chauffeur)
admin.site.register(AdminProfil)