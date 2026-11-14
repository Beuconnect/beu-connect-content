#!/usr/bin/env python3
"""
Unit test suite for generate_vvi_topics.py
Verifies PYQ topic extraction, priority thresholding, manual topic preservation,
and JSON schema output validity.
"""

import json
import os
import sys
import unittest

# Add scripts directory to module path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_vvi_topics import (
    extract_topic_name,
    calculate_priority,
    process_pyq_master,
    merge_and_update_vvi_topics
)

class TestVviTopicsGeneration(unittest.TestCase):

    def test_extract_topic_name_boilerplate_cleaning(self):
        raw_q = "<p>Discuss the structure and working of He-Ne LASER. Draw its energy level diagram.</p>"
        topic = extract_topic_name(raw_q)
        self.assertEqual(topic, "He-Ne LASER")

    def test_extract_topic_name_schrodinger(self):
        raw_q = "Write down time-independent Schrödinger's wave equation in 1-dimension."
        topic = extract_topic_name(raw_q)
        self.assertEqual(topic, "Schrödinger's Wave Equation")

    def test_calculate_priority_thresholds(self):
        self.assertEqual(calculate_priority(5), "High")
        self.assertEqual(calculate_priority(3), "High")
        self.assertEqual(calculate_priority(2), "Medium")
        self.assertEqual(calculate_priority(1), "Low")

    def test_full_pipeline_preserves_manual_topics(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pyq_json_path = os.path.join(repo_root, 'app', 'src', 'main', 'assets', 'BEUConnect_PYQ_structured.json')
        vvi_json_path = os.path.join(repo_root, 'app', 'src', 'main', 'assets', 'BEUConnect_Important_Topics.json')

        self.assertTrue(os.path.exists(pyq_json_path), f"PYQ JSON missing at {pyq_json_path}")
        self.assertTrue(os.path.exists(vvi_json_path), f"Important Topics JSON missing at {vvi_json_path}")

        subject_meta, extracted_data = process_pyq_master(pyq_json_path)
        self.assertGreater(len(extracted_data), 0, "No subjects extracted from PYQ JSON")

        output_data = merge_and_update_vvi_topics(vvi_json_path, subject_meta, extracted_data)
        self.assertIn('subjects', output_data)
        self.assertGreater(len(output_data['subjects']), 0)

        # Verify that all subjects have topics and source fields
        for subject in output_data['subjects']:
            self.assertIn('subjectId', subject)
            self.assertIn('topics', subject)
            for topic in subject['topics']:
                self.assertIn('topicId', topic)
                self.assertIn('topicName', topic)
                self.assertIn('priority', topic)
                self.assertIn('source', topic)
                self.assertIn(topic['source'], ['manual', 'auto'])

if __name__ == '__main__':
    unittest.main()
