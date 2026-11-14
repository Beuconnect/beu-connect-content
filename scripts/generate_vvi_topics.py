#!/usr/bin/env python3
"""
BEU Connect - Automatic PYQ-Based VVI Topics Generation Script

Reads PYQ master dataset (BEUConnect_PYQ_structured.json), extracts academic topics
branch-wise, semester-wise, and subject-wise, calculates frequency/years/priority,
and merges them with manually curated topics in BEUConnect_Important_Topics.json.
"""

import json
import os
import re
import sys
from datetime import datetime
from collections import defaultdict

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# Prefix phrases to remove when extracting academic topic titles from question text
BOILERPLATE_PREFIXES = [
    r'^[Qq]\.\s*\d+\s*(?:Choose the correct option|Solve both questions|Write short note[s]? on|Write note[s]? on|Answer the following|Discuss|Explain)?[:\.\s]*',
    r'^Write short note[s]? on (?:any \w+ of )?the following[:\.\s]*',
    r'^Write note[s]? on (?:any \w+ of )?the following[:\.\s]*',
    r'^Write down (?:the |time-independent |time-dependent )?',
    r'^Discuss (?:the )?(?:structure and working of|construction and working of|working principle of|motion of)?\s*',
    r'^Explain (?:the )?(?:structure and working of|working principle of|significance of|effect of)?\s*',
    r'^Derive (?:an|the)?\s*(?:expression for|differential equation for|equation for)?\s*',
    r'^What (?:is|are) (?:a|an|the)?\s*',
    r'^State and explain (?:the )?',
    r'^State (?:the )?',
    r'^Differentiate between ',
    r'^Distinguish (?:between|among) ',
    r'^Mention (?:the )?',
    r'^Prove that ',
    r'^Obtain (?:the )?',
]

# Standard replacements to clean and normalize topic titles
TOPIC_NORMALIZATIONS = {
    r'\bhe-ne laser\b': 'He-Ne LASER',
    r'\bruby laser\b': 'Ruby LASER',
    r'\bsemiconductor laser\b': 'Semiconductor LASER',
    r'\b3-level laser\b': '3-Level LASER',
    r'\b4-level laser\b': '4-Level LASER',
    r'\bschr[oö]dinger\'?s?\b': "Schrödinger's Wave Equation",
    r'\bkronig-penney model\b': 'Kronig-Penney Model',
    r'\bbloch\'?s? theorem\b': "Bloch's Theorem",
    r'\bpoynting theorem\b': 'Poynting Theorem',
    r'\bpoynting vector\b': 'Poynting Vector',
    r'\bmaxwell\'?s? equations?\b': "Maxwell's Equations",
    r'\bmichelson\'?s? interferometer\b': "Michelson's Interferometer",
    r'\bcompton shift\b': 'Compton Shift',
    r'\bcompton effect\b': 'Compton Effect',
    r'\bcompton scattering\b': 'Compton Scattering',
    r'\bdamped harmonic oscillator\b': 'Damped Harmonic Oscillator',
    r'\bforced harmonic oscillator\b': 'Forced Harmonic Oscillator',
    r'\bsimple harmonic oscillator\b': 'Simple Harmonic Oscillator',
    r'\bnewton\'?s? ring experiment\b': "Newton's Ring Experiment",
    r'\bnewton\'?s? rings\b': "Newton's Rings",
    r'\bfermi level\b': 'Fermi Level',
    r'\bfermi energy\b': 'Fermi Energy',
    r'\bheisenberg\'?s? uncertainty principle\b': "Heisenberg's Uncertainty Principle",
    r'\blorentz force\b': 'Lorentz Force',
    r'\bcoriolis (?:effect|acceleration)\b': 'Coriolis Effect',
    r'\bfraunhofer\'?s? (?:single slit )?diffraction\b': "Fraunhofer Single Slit Diffraction",
    r'\b optical fibre communication\b': 'Optical Fibre Communication',
    r'\beinstein\'?s? photo-electric equation\b': "Einstein's Photo-Electric Equation",
    r'\bsingle-phase transformer\b': 'Single-Phase Transformer',
    r'\binduction motor\b': 'Induction Motor',
    r'\bdc generator\b': 'DC Generator',
    r'\bdc motor\b': 'DC Motor',
    r'\bnorton theorem\b': 'Norton Theorem',
    r'\bthevenin theorem\b': 'Thevenin Theorem',
    r'\bpower transfer theorem\b': 'Maximum Power Transfer Theorem',
    r'\bsuperposition theorem\b': 'Superposition Theorem',
    r'\beddy current loss\b': 'Eddy Current Loss',
    r'\bearthing\b': 'Earthing Systems',
    r'\bphasor\b': 'Phasor Diagrams & AC Circuits',
    r'\bbridge rectifier\b': 'Bridge Rectifier',
    r'\bmosfet\b': 'MOSFET Characteristics & Applications',
    r'\bzener diode\b': 'Zener Diode',
    r'\bbjt\b': 'Bipolar Junction Transistor (BJT)',
    r'\bjfet\b': 'JFET Characteristics',
    r'\bp-n junction diode\b': 'P-N Junction Diode',
    r'\bop-amp\b|\boperational amplifier\b': 'Operational Amplifier (Op-Amp)',
}

def clean_html_text(html_content):
    """Extract clean text from HTML content removing options lists and headers."""
    if not html_content:
        return ""
    if BeautifulSoup:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Remove options lists, instructions, paper details
        for elem in soup.find_all(['ol', 'ul'], class_=['options-list', 'paper-instructions']):
            elem.decompose()
        for elem in soup.find_all('header', class_='paper-header'):
            elem.decompose()
        return soup.get_text(separator=' ')
    else:
        # Regex fallback
        text = re.sub(r'<ol class="options-list">.*?</ol>', '', html_content, flags=re.DOTALL)
        text = re.sub(r'<div class="paper-instructions">.*?</div>', '', text, flags=re.DOTALL)
        text = re.sub(r'<header class="paper-header">.*?</header>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        return text

def extract_subquestions_from_html(html_content):
    """Extract individual question items from HTML paper."""
    questions = []
    if BeautifulSoup:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Find all li.sub-question elements
        sub_qs = soup.find_all('li', class_='sub-question')
        for sq in sub_qs:
            # Remove options list inside sub-question if any
            for opts in sq.find_all(['ol', 'ul'], class_='options-list'):
                opts.decompose()
            q_text = sq.get_text(separator=' ').strip()
            if q_text:
                questions.append(q_text)
    else:
        # Regex fallback for <li class="sub-question">
        matches = re.findall(r'<li class="sub-question"[^>]*>(.*?)</li>', html_content, flags=re.DOTALL)
        for m in matches:
            clean_m = re.sub(r'<ol class="options-list">.*?</ol>', '', m, flags=re.DOTALL)
            clean_m = re.sub(r'<[^>]+>', ' ', clean_m).strip()
            if clean_m:
                questions.append(clean_m)
    return questions

def extract_year_from_title(title):
    """Extract 4-digit exam year from title string."""
    if not title or not isinstance(title, str):
        return None
    match = re.search(r'20\d{2}', title)
    return int(match.group(0)) if match else None

def extract_topic_name(q_text):
    """Clean boilerplate from question text and return concise academic topic name."""
    text = q_text.strip()

    # Remove LaTeX markers \( ... \)
    text = re.sub(r'\\\(.*?\\\)', '', text)
    # Remove marks indicator e.g. [14], [10], [7×2=14]
    text = re.sub(r'\[[\d×=]+\]', '', text)
    # Remove trailing/leading punctuation or whitespace
    text = text.strip(' .,;:?-')

    # Strip boilerplate prefix
    for pattern in BOILERPLATE_PREFIXES:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()

    # Apply normalization rules
    lower_text = text.lower()
    for norm_pattern, target_title in TOPIC_NORMALIZATIONS.items():
        if re.search(norm_pattern, lower_text):
            return target_title

    # Capitalize title nicely if no direct normalization matched
    # Cut off if text is too long (take first sentence or clause up to 60 chars)
    first_clause = re.split(r'[\.\?\!\;\:\n]', text)[0].strip()
    if len(first_clause) > 60:
        words = first_clause.split()
        first_clause = " ".join(words[:6])

    # Capitalize words
    words = [w.capitalize() if len(w) > 3 or w.isupper() else w for w in first_clause.split()]
    title = " ".join(words).strip(' .,;:?-')

    return title if len(title) >= 3 else None

def generate_topic_id(subject_id, topic_name):
    """Create a URL-safe topicId slug."""
    prefix = subject_id.lower().replace(" ", "-")[:8]
    slug = re.sub(r'[^a-z0-9]+', '-', topic_name.lower()).strip('-')
    return f"{prefix}-{slug}"

def extract_subtopics_from_text(text):
    """Extract key subtopics / aspects from question text."""
    subtopics = set()
    lowered = text.lower()
    if "deriv" in lowered or "proof" in lowered:
        subtopics.add("Derivation / proof")
    if "diagram" in lowered or "sketch" in lowered or "plot" in lowered:
        subtopics.add("Diagrams")
    if "working" in lowered or "structure" in lowered or "construction" in lowered:
        subtopics.add("Working Principle")
    if "application" in lowered or "uses" in lowered:
        subtopics.add("Applications")
    if "difference" in lowered or "distinguish" in lowered or "compare" in lowered:
        subtopics.add("Differences / comparison")
    if "numerical" in lowered or "calculate" in lowered or "compute" in lowered:
        subtopics.add("Numerical problems")
    if "definition" in lowered or "define" in lowered:
        subtopics.add("Definition")
    return list(subtopics)

def calculate_priority(appearance_count):
    """Determine High, Medium, or Low priority based on appearance count."""
    if appearance_count >= 3:
        return "High"
    elif appearance_count == 2:
        return "Medium"
    else:
        return "Low"

def map_pyq_subject_code_to_vvi_id(code, name):
    """Map PYQ subject codes/names to Important Topics subjectId."""
    code_lower = code.lower().strip()
    name_lower = name.lower().strip()

    if "physics" in name_lower or code_lower in ["phy", "100201", "105201", "103201"]:
        return "engineering-physics"
    if "chemistry" in name_lower or code_lower in ["che", "100202"]:
        return "engineering-chemistry"
    if "electrical" in name_lower or code_lower in ["bee", "100203"]:
        return "basic-electrical-engineering"
    if "programming" in name_lower or "pps" in name_lower or code_lower in ["pps", "100204"]:
        return "programming-for-problem-solving"
    if "graphics" in name_lower or "egd" in name_lower or code_lower in ["egd", "100205"]:
        return "engineering-graphics-design"
    if "math" in name_lower or code_lower in ["math1", "math2", "em", "100101", "100201"]:
        return "engineering-mathematics"
    if "english" in name_lower or "communicative" in name_lower or code_lower in ["eng", "ce"]:
        return "communicative-english"
    if "mechanical" in name_lower or code_lower in ["eme"]:
        return "elements-of-mechanical-engineering"
    if "electronics" in name_lower or code_lower in ["electronics", "be"]:
        return "basic-electronics"
    if "biology" in name_lower or code_lower in ["bio", "be"]:
        return "biology-for-engineers"

    # Fallback slug
    return re.sub(r'[^a-z0-9]+', '-', name_lower).strip('-')

def process_pyq_master(pyq_json_path):
    """Process PYQ dataset and extract topic occurrences per subject."""
    with open(pyq_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Subject -> Topic Name -> {years: set(), text_samples: [], subtopics: set()}
    extracted_data = defaultdict(lambda: defaultdict(lambda: {
        'years': set(),
        'subtopics': set(),
        'questions': []
    }))

    subject_meta = {}

    # Iterate through all top-level keys in PYQ JSON (e.g. "qp1", "qp2", ...)
    subject_list = []
    if isinstance(data, dict):
        for key, val in data.items():
            if isinstance(val, list):
                subject_list.extend(val)
    elif isinstance(data, list):
        subject_list = data

    for item in subject_list:
        code = item.get('code', '')
        name = item.get('name', '')
        sem_group = item.get('semesterGroup', '1st-2nd')
        papers = item.get('papers', [])

        subject_id = map_pyq_subject_code_to_vvi_id(code, name)
        subject_meta[subject_id] = {
            'subjectId': subject_id,
            'subjectName': name,
            'code': code,
            'semesterGroup': sem_group
        }

        for paper in papers:
            exam_title = paper.get('examTitle', '')
            html_content = paper.get('html', '')
            year = extract_year_from_title(exam_title)
            if not year:
                continue

            sub_qs = extract_subquestions_from_html(html_content)
            for q in sub_qs:
                topic_name = extract_topic_name(q)
                if topic_name and len(topic_name) >= 3:
                    entry = extracted_data[subject_id][topic_name]
                    entry['years'].add(year)
                    entry['subtopics'].update(extract_subtopics_from_text(q))
                    entry['questions'].append(q)

    return subject_meta, extracted_data

def merge_and_update_vvi_topics(important_topics_path, subject_meta, extracted_data):
    """Merge auto-extracted topics into Important Topics JSON while preserving manual topics."""
    existing_data = {}
    if os.path.exists(important_topics_path):
        with open(important_topics_path, 'r', encoding='utf-8') as f:
            try:
                existing_data = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load existing Important Topics JSON: {e}")

    subjects = existing_data.get('subjects', [])
    subject_map = {s.get('subjectId'): s for s in subjects if s.get('subjectId')}

    # Process each subject extracted from PYQ master
    for subj_id, topics_dict in extracted_data.items():
        meta = subject_meta.get(subj_id, {})
        if subj_id not in subject_map:
            # Create new subject entry if it doesn't exist
            subject_map[subj_id] = {
                "subjectId": subj_id,
                "branch": "ALL",
                "semester": 1,
                "subjectName": meta.get('subjectName', subj_id.replace('-', ' ').title()),
                "topics": []
            }

        subj_entry = subject_map[subj_id]
        existing_topics = subj_entry.get('topics', [])

        # Ensure all existing manual topics have source="manual"
        topic_dict_by_name = {}
        for t in existing_topics:
            if 'source' not in t or not t['source']:
                t['source'] = 'manual'
            norm_name = t.get('topicName', '').lower().strip()
            topic_dict_by_name[norm_name] = t

        # Build list of new automatic topics and update manual matches
        auto_topic_list = []
        for top_name, top_info in topics_dict.items():
            years_list = sorted(list(top_info['years']))
            count = len(years_list)
            priority = calculate_priority(count)
            subtopics_list = sorted(list(top_info['subtopics']))
            if not subtopics_list:
                subtopics_list = ["Key Concepts", "Exam Questions"]

            years_str = ", ".join(map(str, years_list))
            sub_str = ", ".join(subtopics_list[:3])
            rev_note = f"Asked in {years_str}. Cover {sub_str}."

            norm_name = top_name.lower().strip()
            if norm_name in topic_dict_by_name:
                # Update existing manual topic appearance stats without touching its title or manual curation
                existing_t = topic_dict_by_name[norm_name]
                existing_years = set(existing_t.get('yearsAppeared', []))
                existing_years.update(years_list)
                existing_t['yearsAppeared'] = sorted(list(existing_years))
                existing_t['appearanceCount'] = max(existing_t.get('appearanceCount', 0), len(existing_t['yearsAppeared']))
                existing_t['priority'] = calculate_priority(existing_t['appearanceCount'])
            else:
                # Add new automatic topic
                topic_id = generate_topic_id(subj_id, top_name)
                auto_topic_list.append({
                    "topicId": topic_id,
                    "topicName": top_name,
                    "priority": priority,
                    "yearsAppeared": years_list,
                    "appearanceCount": count,
                    "subtopics": subtopics_list,
                    "revisionNote": rev_note,
                    "verified": False,
                    "source": "auto"
                })

        # Remove outdated auto topics that no longer exist in the extracted PYQ dataset
        updated_topics = []
        for t in existing_topics:
            if t.get('source') == 'auto':
                norm_name = t.get('topicName', '').lower().strip()
                if norm_name in [tn.lower().strip() for tn in topics_dict.keys()]:
                    updated_topics.append(t)
            else:
                # Always preserve manual topics
                updated_topics.append(t)

        # Append new auto topics
        updated_topics.extend(auto_topic_list)

        # Ensure all topics have source field explicitly set
        for t in updated_topics:
            if 'source' not in t or not t['source']:
                t['source'] = 'manual'

        # Sort topics by appearance count descending
        updated_topics.sort(key=lambda x: x.get('appearanceCount', 0), reverse=True)
        subj_entry['topics'] = updated_topics

    # Ensure all subjects across output_data have source field set for all topics
    for subj in subject_map.values():
        for t in subj.get('topics', []):
            if 'source' not in t or not t['source']:
                t['source'] = 'manual'

    output_data = {
        "schemaVersion": existing_data.get('schemaVersion', 1),
        "dataVersion": "1.0.3",
        "lastUpdated": datetime.now().strftime("%Y-%m-%d"),
        "subjects": list(subject_map.values())
    }

    return output_data

def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pyq_json_path = os.path.join(repo_root, 'app', 'src', 'main', 'assets', 'BEUConnect_PYQ_structured.json')
    vvi_json_path = os.path.join(repo_root, 'app', 'src', 'main', 'assets', 'BEUConnect_Important_Topics.json')

    if len(sys.argv) > 1:
        pyq_json_path = sys.argv[1]
    if len(sys.argv) > 2:
        vvi_json_path = sys.argv[2]

    if not os.path.exists(pyq_json_path):
        print(f"Error: PYQ dataset file not found at {pyq_json_path}")
        sys.exit(1)

    print(f"Processing PYQ Master JSON: {pyq_json_path}")
    subject_meta, extracted_data = process_pyq_master(pyq_json_path)

    print(f"Extracted topics for {len(extracted_data)} subjects.")
    output_data = merge_and_update_vvi_topics(vvi_json_path, subject_meta, extracted_data)

    # Validate output data
    if not output_data.get('subjects'):
        print("Error: Generated dataset has no subjects. Preserving existing file.")
        sys.exit(1)

    with open(vvi_json_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"Successfully generated VVI Topics JSON at {vvi_json_path}")
    sys.exit(0)

if __name__ == '__main__':
    main()
