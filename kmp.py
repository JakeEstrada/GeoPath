import json

with open('tasks.json', 'r') as f:
    tasks_data = json.load(f)
    tasks_list = tasks_data['tasks']

def kmp_search(text, pattern):
    def compute_lps(pattern):
        lps = [0] * len(pattern)
        length = 0
        i = 1
        while i < len(pattern):
            if pattern[i] == pattern[length]:
                length += 1
                lps[i] = length
                i += 1
            else:
                if length != 0:
                    length = lps[length - 1]
                else:
                    lps[i] = 0
                    i += 1
        return lps

    lps = compute_lps(pattern)
    result = []
    i = j = 0
    while i < len(text):
        if pattern[j].lower() == text[i].lower():  # Case-insensitive search
            i += 1
            j += 1
        if j == len(pattern):
            result.append(i - j)
            j = lps[j - 1]
        elif i < len(text) and pattern[j].lower() != text[i].lower():
            if j != 0:
                j = lps[j - 1]
            else:
                i += 1
    return result

def search_tasks_by_building(query):
    matches = []
    for task in tasks_list:
        building_name = task['building_name']
        if kmp_search(building_name, query):
            matches.append(task)
    return matches

