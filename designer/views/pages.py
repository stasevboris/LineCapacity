from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from django.contrib.auth import logout, authenticate, login
from django.urls import reverse

from ..models import Organization


def editor_view(request):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next=/")

    is_super = request.user.is_superuser
    is_staff = request.user.is_staff
    can_access_admin = is_super or is_staff

    if is_super:
        organizations = Organization.objects.all()
    else:
        user_org = request.user.profile.organization if hasattr(request.user, 'profile') else None
        organizations = (
            Organization.objects.filter(id=user_org.id) if user_org
            else Organization.objects.none()
        )

    user_org = (
        request.user.profile.organization
        if hasattr(request.user, 'profile') else None
    )
    return render(request, 'designer/index.html', {
        'organizations': organizations,
        'is_super': is_super,
        'can_access_admin': can_access_admin,
        'current_org_id': user_org.id if user_org else None,
        'current_org_name': user_org.name if user_org else '',
    })


def admin_panel_view(request):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next=/admin-panel/")

    is_super = request.user.is_superuser
    is_admin = request.user.is_staff

    if not (is_super or is_admin):
        return HttpResponseForbidden(
            "<div style='font-family: sans-serif; text-align: center; margin-top: 50px;'>"
            "<h1 style='color: #ff5252;'>Доступ запрещен ⛔</h1>"
            "<p>Эта страница доступна только администраторам.</p>"
            "<a href='/' style='color: #2563eb; text-decoration: none; font-weight: bold;'>"
            "← Вернуться в редактор</a>"
            "</div>"
        )

    if is_super:
        organizations = Organization.objects.all()
    else:
        user_org = request.user.profile.organization if hasattr(request.user, 'profile') else None
        organizations = (
            Organization.objects.filter(id=user_org.id) if user_org
            else Organization.objects.none()
        )

    return render(request, 'designer/admin_panel.html', {
        'organizations': organizations,
        'is_super': is_super,
    })


def logout_view(request):
    logout(request)
    return redirect('login')


def login_view(request):
    next_url = request.GET.get('next') or request.POST.get('next') or '/'
    error = None

    if request.user.is_authenticated:
        return redirect(next_url)

    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            return redirect(next_url)
        error = 'Неверный логин или пароль'

    return render(request, 'designer/login.html', {
        'error': error,
        'next': next_url,
    })
