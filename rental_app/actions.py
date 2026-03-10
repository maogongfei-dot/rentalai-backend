from ui import show_listings

def delete_listing(state):
    listings = state["listings"]   # 让原逻辑继续用 listings 这个名字

    if not listings:
        print("暂无房源可删除。")
        return state

    show_listings(listings)

    raw = input("请输入要删除的房源编号(1-{})，或输入0取消: ".format(len(listings))).strip()
    if not raw.isdigit():
        print("输入必须是数字。")
        return state

    idx = int(raw)
    if idx == 0:
        print("已取消删除。")
        return state

    if not (1 <= idx <= len(listings)):
        print("编号超出范围。")
        return state

    removed = listings.pop(idx - 1)
    print(f"✅ 已删除：{removed.get('title', '该房源')}")
    return state

def edit_listing(state):
    listings = state["listings"]

    if not listings:
        print("暂无房源可编辑。")
        return state

    show_listings(listings)

    raw = input(f"请输入要编辑的房源编号 (1-{len(listings)})，或0取消: ").strip()
    if not raw.isdigit():
        print("输入必须是数字。")
        return state

    idx = int(raw)
    if idx == 0:
        print("已取消编辑。")
        return state

    if not (1 <= idx <= len(listings)):
        print("编号超出范围。")
        return state

    house = listings[idx - 1]

    # 下面保留你原来的编辑流程（逐项 input 修改）
    # 例如：
    new_price = input(f"新租金(回车跳过) 当前={house.get('price')}: ").strip()
    if new_price:
        if new_price.isdigit():
            house["price"] = int(new_price)
        else:
            print("租金必须是数字，已跳过该项。")

    print("✅ 编辑完成。")
    return state

def clear_listings(state):
    state["listings"].clear()
    state["ranked_results"] = []      # 顺手把评分缓存也清掉，避免脏数据
    state["last_action"] = "clear"
    print("已清空所有房源。")
    return state

def strip_scores(state):
    listings = state["listings"]
    for h in listings:
        if isinstance(h, dict) and "_score" in h:
            h.pop("_score", None)

