#Moves and combinations
import random

#Puzzle moves for generating scrambles
small_cubes = ['R', 'R\'', 'R2', 'L', 'L\'', 'L2', 'U', 'U\'', 'U2', 'F', 'F\'', 'F2', 'B', 'B\'', 'B2', 'D', 'D\'',
               'D2']
big_cubes = ['R', 'R\'', 'R2', "Rw", "Rw'", "Rw2",
             'L', 'L\'', 'L2', "Lw", "Lw'", "Lw2",
             'U', 'U\'', 'U2', "Uw", "Uw'", "Uw2",
             'F', 'F\'', 'F2', "Fw", "Fw'", "Fw2",
             'B', 'B\'', 'B2', "Bw", "Bw'", "Bw2",
             'D', 'D\'', 'D2', "Dw", "Dw'", "Dw2"]

#Gets specific puzzle and generates the scramble
def generate_scramble(puzzle):
    match puzzle.lower():
        case "2x2":
            cube = small_cubes; scramble_length = 8
        case "3x3":
            cube = small_cubes; scramble_length = 20
        case "4x4":
            cube = big_cubes; scramble_length = 43
        case "5x5":
            cube = big_cubes; scramble_length = 59
        case _:
            cube = small_cubes; scramble_length = 20

    scrambles = [random.choice(cube)]
    while len(scrambles) < scramble_length:
        move = random.choice(cube)
        if move[0] != scrambles[-1][0]:
            scrambles.append(move)

    return " ".join(scrambles)

#Only for Ao5 and Ao12
def calculate_wca_average(solve_list):

    if len(solve_list) not in [5, 12]:
        return "-"

    times = []
    dnf_count = 0

    for solve in solve_list:
        if solve["is_dnf"] == 1:
            times.append(float('inf'))
            dnf_count += 1
        else:
            times.append(solve["final_time_ms"])

    if dnf_count >= 2:
        return "DNF"

    times.sort()

    times_to_calculate = times[1:-1]

    average = sum(times_to_calculate) / len(times_to_calculate)

    return int(round(average))

#Specifically for Ao100
def calculate_wca_ao100(solve_list):
    if len(solve_list) != 100:
        return "-"

    times = []
    dnf_count = 0

    for solve in solve_list:
        if solve["is_dnf"] == 1:
            times.append(float('inf'))
            dnf_count += 1
        else:
            times.append(solve["final_time_ms"])

    if dnf_count >= 6:
        return "DNF"

    times.sort()

    times_to_calculate = times[5:-5]

    average = sum(times_to_calculate) / len(times_to_calculate)

    return int(round(average))

#Calculates the session mean (In a specific tab)
def calculate_session_mean(tab_data):

    valid_times = [data["final_time_ms"] for data in tab_data if data["is_dnf"] != 1]

    if not valid_times:
        return "-", 0

    mean_ms = sum(valid_times) / len(valid_times)

    return int(round(mean_ms)), len(valid_times)