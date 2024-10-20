import os

SONGS_FOLDER = 'D:\\Other\\Mega\\MEGAsync\\Dance-Games\\ITGMania\\Songs'
MIN_DIFF = 7
MAX_DIFF = 10
RIGHT_SONG_PERCENTAGE = 0.25
MAX_MISTAKE_PERCENTAGE = 0.1

def read_file_with_encodings(filepath, encodings=['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']):
    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as file:
                return file.readlines()
        except UnicodeDecodeError:
            print(f"Failed to decode {filepath} with {encoding}. Trying next encoding.")
    print(f"Error parsing {filepath}: Unable to decode with any of the provided encodings.")
    return None

def parse_sm_file(filepath, pack_name, song_name):
    charts = []
    dance_single_difficulties = []

    lines = read_file_with_encodings(filepath)
    if lines is None:
        return charts, dance_single_difficulties

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith('#NOTES:'):
            note_fields = []
            line_content = line[len('#NOTES:'):].strip()
            line_content = line_content.split('//')[0].strip()
            if line_content:
                note_fields.append(line_content)
            i += 1
            while len(note_fields) < 6 and i < len(lines):
                next_line = lines[i].strip()
                next_line = next_line.split('//')[0].strip()
                if next_line:
                    note_fields.append(next_line)
                i += 1

            if len(note_fields) >= 5:
                stepstype = note_fields[0].strip().rstrip(':')
                meter_str = note_fields[3].strip().rstrip(':')
                try:
                    meter = int(meter_str)
                except ValueError:
                    meter = None

                if stepstype == 'dance-single' and meter is not None:
                    dance_single_difficulties.append((pack_name, song_name, meter))
                    if MIN_DIFF <= meter <= MAX_DIFF:
                        charts.append((pack_name, song_name, meter))

            while i < len(lines) and not lines[i].strip() == ';':
                i += 1
            if i < len(lines):
                i += 1
        else:
            i += 1

    return charts, dance_single_difficulties

def parse_ssc_file(filepath, pack_name, song_name):
    charts = []
    dance_single_difficulties = []

    lines = read_file_with_encodings(filepath)
    if lines is None:
        return charts, dance_single_difficulties

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith('#NOTEDATA:'):
            i += 1
            stepstype = None
            meter = None

            while i < len(lines):
                line = lines[i].strip()
                if line.startswith('#STEPSTYPE:'):
                    stepstype = line[len('#STEPSTYPE:'):].strip().rstrip(';')
                    i += 1
                elif line.startswith('#METER:'):
                    meter_str = line[len('#METER:'):].strip().rstrip(';')
                    try:
                        meter = int(meter_str)
                    except ValueError:
                        meter = None
                    i += 1
                elif line.startswith('#NOTES:'):
                    i += 1
                    while i < len(lines) and not lines[i].strip() == ';':
                        i += 1
                    if i < len(lines):
                        i += 1
                    break
                else:
                    i += 1

            if stepstype == 'dance-single' and meter is not None:
                dance_single_difficulties.append((pack_name, song_name, meter))
                if MIN_DIFF <= meter <= MAX_DIFF:
                    charts.append((pack_name, song_name, meter))
        else:
            i += 1

    return charts, dance_single_difficulties

def process_song(song_folder, pack_name):
    ssc_file = None
    sm_file = None

    for root, _, files in os.walk(song_folder):
        for file in files:
            if file.endswith('.ssc'):
                ssc_file = os.path.join(root, file)
            elif file.endswith('.sm'):
                sm_file = os.path.join(root, file)

    if ssc_file:
        return parse_ssc_file(ssc_file, pack_name, os.path.basename(song_folder))
    elif sm_file:
        return parse_sm_file(sm_file, pack_name, os.path.basename(song_folder))

    return [], []

def main():
    debug_lines = []
    result_lines = []
    potential_mistakes = []

    for pack in os.listdir(SONGS_FOLDER):
        pack_folder = os.path.join(SONGS_FOLDER, pack)
        if not os.path.isdir(pack_folder):
            continue

        song_count = 0
        parsed_song_count = 0
        valid_chart_count = 0

        for song in os.listdir(pack_folder):
            song_folder = os.path.join(pack_folder, song)
            if not os.path.isdir(song_folder):
                continue

            song_count += 1

            valid_charts, all_dance_single_difficulties = process_song(song_folder, pack)

            if all_dance_single_difficulties:
                parsed_song_count += 1

            for pack_name, song_name, meter in all_dance_single_difficulties:
                debug_lines.append(f"{pack_name}/{song_name}: {meter}")

            if valid_charts:
                valid_chart_count += 1

        if song_count != parsed_song_count:
            potential_mistakes.append(f"{pack} - Expected: {song_count}, Parsed: {parsed_song_count}")

        if song_count > 0 and valid_chart_count / song_count < RIGHT_SONG_PERCENTAGE:
            mistake_percentage = (song_count - parsed_song_count) / song_count
            if mistake_percentage <= MAX_MISTAKE_PERCENTAGE:
                result_lines.append(pack)

    with open('debug.txt', 'w', encoding='utf-8') as debug_file:
        debug_file.write('\n'.join(debug_lines))

    with open('result.txt', 'w', encoding='utf-8') as result_file:
        result_file.write('\n'.join(result_lines))

    if potential_mistakes:
        with open('potential-mistake.txt', 'w', encoding='utf-8') as mistake_file:
            mistake_file.write('\n'.join(potential_mistakes))

main()
