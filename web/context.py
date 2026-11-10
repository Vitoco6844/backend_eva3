from accounts.permissions import can_operate


def public_context(request):
    selected = request.session.get("rental_selection", [])
    selected = selected if isinstance(selected, list) else []
    return {
        "operator": can_operate(request.user),
        "selection_count": len(
            set(value for value in selected if type(value) is int and value > 0)
        ),
    }
