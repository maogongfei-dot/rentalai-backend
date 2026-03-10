import json
import os

DATA_FILE = "area_data.json"


def load_area_data():
    """从JSON文件读取地区数据"""
    if not os.path.exists(DATA_FILE):
        return []

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_area_data(area_list):
    """保存地区数据到JSON"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(area_list, f, indent=4)

def add_area_info(area_list):
    """新增地区信息"""

    postcode = input("Postcode: ")
    area_name = input("Area name: ")

    safety_score = float(input("Safety score (0-10): "))
    transport_score = float(input("Transport score (0-10): "))
    shopping_score = float(input("Shopping score (0-10): "))
    quiet_score = float(input("Quiet score (0-10): "))

    notes = input("Notes: ")

    overall_area_score = (
        safety_score + transport_score + shopping_score + quiet_score
    ) / 4

    area = {
        "postcode": postcode,
        "area_name": area_name,
        "safety_score": safety_score,
        "transport_score": transport_score,
        "shopping_score": shopping_score,
        "quiet_score": quiet_score,
        "overall_area_score": overall_area_score,
        "notes": notes,
    }

    area_list.append(area)

    print("Area added successfully.")

def view_area_info(area_list):
    """查看地区信息"""

    if not area_list:
        print("No area data found.")
        return

    for area in area_list:
        print("-----------")
        print("Postcode:", area["postcode"])
        print("Area:", area["area_name"])
        print("Safety:", area["safety_score"])
        print("Transport:", area["transport_score"])
        print("Shopping:", area["shopping_score"])
        print("Quiet:", area["quiet_score"])
        print("Overall score:", area["overall_area_score"])
        print("Notes:", area["notes"])

def area_menu():
    area_list = load_area_data()

    while True:
        print("\n--- Area Module ---")
        print("1. Add area info")
        print("2. View area info")
        print("3. Save area data")
        print("4. Reload area data")
        print("5. Exit")

        choice = input("Select: ")

        if choice == "1":
            add_area_info(area_list)

        elif choice == "2":
            view_area_info(area_list)

        elif choice == "3":
            save_area_data(area_list)
            print("Saved.")

        elif choice == "4":
            area_list = load_area_data()
            print("Reloaded.")

        elif choice == "5":
            break

        else:
            print("Invalid option.")

import json
import os

DATA_FILE = "area_data.json"


def get_area_score(postcode):
    if not os.path.exists(DATA_FILE):
        return 0

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    postcode = postcode.strip().upper()

    for area in data:
        if area.get("postcode", "").strip().upper() == postcode:
            return area.get("overall_area_score", 0)

    return 0

if __name__ == "__main__":
    area_menu()