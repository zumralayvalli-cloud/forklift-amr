import heapq


# Noktalar ve aralarındaki mesafeler
# Bu değerler örnektir, gerçek yarışma ölçümleri değildir.
graph = {
    "START": {"A1": 2, "N1": 5},
    "A1": {"START": 2, "A2": 3, "N1": 2},
    "A2": {"A1": 3, "N2": 4},
    "N1": {"START": 5, "A1": 2, "N2": 2},
    "N2": {"N1": 2, "A2": 4, "KAPI1": 3},
    "KAPI1": {"N2": 3, "B1": 2},
    "B1": {"KAPI1": 2}
}


def shortest_path(start, goal):
    queue = [(0, start, [start])]
    visited = set()

    while queue:
        distance, node, path = heapq.heappop(queue)

        if node in visited:
            continue

        visited.add(node)

        if node == goal:
            return distance, path

        for neighbor, weight in graph[node].items():
            if neighbor not in visited:
                heapq.heappush(
                    queue,
                    (distance + weight, neighbor, path + [neighbor])
                )

    return None, []


if __name__ == "__main__":
    distance, path = shortest_path("A2", "B1")

    print("Rota:", " → ".join(path))
    print("Toplam mesafe:", distance)