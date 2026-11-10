from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from inventory.models import Category
from inventory.catalog import public_assets, prepare_asset


def home(request):
    assets = [prepare_asset(a) for a in public_assets()[:6]]
    return render(
        request,
        "public/home.html",
        {
            "assets": assets,
            "categories": Category.objects.filter(
                active=True, asset__in=public_assets()
            ).distinct(),
        },
    )


def catalog(request):
    qs = public_assets()
    q = request.GET.get("q", "")[:100].strip()
    category = request.GET.get("category", "")
    if q:
        qs = qs.filter(name__icontains=q)
    if category:
        qs = (
            qs.filter(category_id=int(category))
            if category.isascii()
            and category.isdecimal()
            and len(category) <= 19
            and int(category) <= 9223372036854775807
            else qs.none()
        )
    assets = [prepare_asset(a) for a in qs]
    if request.GET.get("available") == "1":
        assets = [a for a in assets if a.requestable]
    page = Paginator(assets, 12).get_page(request.GET.get("page"))
    return render(
        request,
        "public/catalog.html",
        {
            "page": page,
            "q": q,
            "selected_category": category,
            "available": request.GET.get("available") == "1",
            "categories": Category.objects.filter(active=True),
        },
    )


def tool(request, pk):
    asset = prepare_asset(get_object_or_404(public_assets(), pk=pk))
    return render(request, "public/tool.html", {"asset": asset})
