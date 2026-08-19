# Analyst Feedback Guide

Use the existing immutable investigation feedback outcomes: accepted, rejected, modified, false_positive, and escalated. Record supporting rationale in the feedback reason field.

Use `POST /api/pilot/runs/<run_id>/observations` for product observations only: investigation usability, evidence usefulness, finding-accuracy feedback, missing information, comments, and improvement suggestions. These observations assess Sentinel DNA, never an analyst.
