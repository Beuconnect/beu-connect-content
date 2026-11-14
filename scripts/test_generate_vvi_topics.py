import unittest

from generate_vvi_topics import exam_year, normalize, question_texts, refresh


class GeneratorTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize("Single-Phase Transformer"), "single phase transformer")

    def test_extract_year(self):
        self.assertEqual(exam_year({"examTitle": "B.Tech 2nd Semester Examination, 2026"}), 2026)

    def test_question_texts(self):
        html = '<div class="sub-question"><p>Define soil mechanics.</p></div>'
        self.assertEqual(question_texts(html), ["Define soil mechanics."])

    def test_refresh_preserves_and_adds_only_supported_year(self):
        pyq = {"qp1": [{
            "name": "Sample Subject", "semesterGroup": "1st-2nd",
            "papers": [{"examTitle": "Examination 2026",
                        "html": '<li class="sub-question">Explain Darcy Law.</li>'}]
        }]}
        curated = {"schemaVersion": 1, "dataVersion": "1.0.0", "lastUpdated": "2025-01-01",
                   "subjects": [{
                       "subjectId": "sample", "branch": "ALL", "semester": 1,
                       "subjectName": "Sample Subject",
                       "topics": [{
                           "topicId": "darcy-law", "topicName": "Darcy Law",
                           "priority": "High", "yearsAppeared": [2024],
                           "appearanceCount": 1, "subtopics": [],
                           "revisionNote": "Keep this note.", "verified": True
                       }]
                   }]}
        result, audit = refresh(pyq, curated)
        topic = result["subjects"][0]["topics"][0]
        self.assertEqual(topic["yearsAppeared"], [2024, 2026])
        self.assertEqual(topic["appearanceCount"], 2)
        self.assertEqual(topic["revisionNote"], "Keep this note.")
        self.assertTrue(topic["verified"])
        self.assertEqual(audit["newYearsAdded"], 1)


if __name__ == "__main__":
    unittest.main()
