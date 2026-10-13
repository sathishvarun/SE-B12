# mock_data.py

CATEGORIES_DATA = {
    "Masala & Spices": {
        "Malli Thool (Coriander Powder)": [
            {"brand": "Aachi", "sizes": [{"pack": "100g", "price": 38.0, "stock": 40}, {"pack": "500g", "price": 175.0, "stock": 20}]},
            {"brand": "Sakthi", "sizes": [{"pack": "100g", "price": 36.0, "stock": 50}, {"pack": "500g", "price": 170.0, "stock": 15}]},
            {"brand": "Everest", "sizes": [{"pack": "100g", "price": 42.0, "stock": 25}]},
            {"brand": "MTR", "sizes": [{"pack": "200g", "price": 85.0, "stock": 18}]},
        ],
        "Milagai Thool (Chilli Powder)": [
            {"brand": "Aachi", "sizes": [{"pack": "100g", "price": 45.0, "stock": 35}, {"pack": "500g", "price": 210.0, "stock": 20}]},
            {"brand": "Sakthi", "sizes": [{"pack": "100g", "price": 42.0, "stock": 45}, {"pack": "500g", "price": 200.0, "stock": 30}]},
            {"brand": "Eastern", "sizes": [{"pack": "200g", "price": 95.0, "stock": 15}]},
        ],
        "Sambar Powder": [
            {"brand": "Aachi", "sizes": [{"pack": "200g", "price": 62.0, "stock": 35}]},
            {"brand": "Sakthi", "sizes": [{"pack": "200g", "price": 60.0, "stock": 40}]},
            {"brand": "MTR", "sizes": [{"pack": "200g", "price": 75.0, "stock": 20}]},
        ],
    },
    "Rice Varieties": {
        "Ponni Boiled Rice": [
            {"brand": "B-Brand Deluxe", "sizes": [{"pack": "25kg", "price": 1450.0, "stock": 30}]},
            {"brand": "Super Star Deluxe", "sizes": [{"pack": "25kg", "price": 1520.0, "stock": 25}]},
            {"brand": "RNR Ponni", "sizes": [{"pack": "10kg", "price": 620.0, "stock": 15}]},
        ],
        "Idli Rice": [
            {"brand": "Udhayam", "sizes": [{"pack": "5kg", "price": 260.0, "stock": 35}]},
            {"brand": "Naga", "sizes": [{"pack": "5kg", "price": 245.0, "stock": 25}]},
        ],
        "Basmati Rice": [
            {"brand": "India Gate (Feast)", "sizes": [{"pack": "5kg", "price": 540.0, "stock": 20}]},
            {"brand": "Daawat (Rozana)", "sizes": [{"pack": "5kg", "price": 450.0, "stock": 18}]},
        ],
    },
    "Dals & Pulses": {
        "Ulundhu (White Whole Urad Dal)": [
            {"brand": "Udhayam", "sizes": [{"pack": "1kg", "price": 168.0, "stock": 40}, {"pack": "500g", "price": 86.0, "stock": 30}]},
            {"brand": "Tata Sampann", "sizes": [{"pack": "1kg", "price": 185.0, "stock": 20}]},
        ],
        "Thuvaram Paruppu (Toor Dal)": [
            {"brand": "Tata Sampann (Unpolished)", "sizes": [{"pack": "1kg", "price": 178.0, "stock": 35}]},
            {"brand": "Udhayam", "sizes": [{"pack": "1kg", "price": 172.0, "stock": 45}]},
        ],
    },
    "Cooking Oils & Ghee": {
        "Nallennai (Gingelly Oil)": [
            {"brand": "Idhayam", "sizes": [{"pack": "1L", "price": 380.0, "stock": 30}, {"pack": "500ml", "price": 195.0, "stock": 25}]},
            {"brand": "Anjali", "sizes": [{"pack": "1L", "price": 360.0, "stock": 15}]},
        ],
        "Sunflower Oil": [
            {"brand": "Gold Winner", "sizes": [{"pack": "1L Pouch", "price": 138.0, "stock": 50}]},
            {"brand": "Fortune Sunlite", "sizes": [{"pack": "1L Pouch", "price": 135.0, "stock": 40}]},
        ],
        "Ghee": [
            {"brand": "Aavin", "sizes": [{"pack": "500ml", "price": 365.0, "stock": 25}]},
            {"brand": "GRB", "sizes": [{"pack": "500ml", "price": 395.0, "stock": 20}]},
        ],
    },
    "Beverages & Cleaning": {
        "Filter Coffee Powder": [
            {"brand": "Narasu's", "sizes": [{"pack": "500g", "price": 245.0, "stock": 30}]},
            {"brand": "Cothas", "sizes": [{"pack": "500g", "price": 260.0, "stock": 20}]},
        ],
        "Washing Powder & Cleaner": [
            {"brand": "Surf Excel (Easy Wash)", "sizes": [{"pack": "1kg", "price": 140.0, "stock": 35}]},
            {"brand": "Vim Dishwash Gel", "sizes": [{"pack": "500ml", "price": 125.0, "stock": 30}]},
        ],
    },
}

# Flattens the nested dictionary into INVENTORY so existing imports work
INVENTORY = []
_id = 1
for category, items in CATEGORIES_DATA.items():
    for item_name, brands in items.items():
        for brand_entry in brands:
            for size in brand_entry["sizes"]:
                INVENTORY.append({
                    "id": _id,
                    "name": f"{brand_entry['brand']} {item_name} ({size['pack']})",
                    "category": category,
                    "price": size["price"],
                    "stock": size["stock"]
                })
                _id += 1