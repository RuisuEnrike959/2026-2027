def access_roles(request):
    user = request.user
    is_admin = user.is_authenticated and user.is_superuser
    can_access_api = is_admin or (
        user.is_authenticated and user.groups.filter(name="API Staff").exists()
    )
    return {
        "can_access_api": can_access_api,
        "is_bookshelf_admin": is_admin,
    }
