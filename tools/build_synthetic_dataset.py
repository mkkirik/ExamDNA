"""Generate the original synthetic physics dataset in examples/synthetic_inputs/.

All questions here were written for ExamDNA. They are not copied or adapted
from any examination board, publisher or past paper.

Outputs:
    physics_bank.json      structured bank of three synthetic papers (what an
                           agent produces after extraction)
    annotations.json       genome annotations (the agent's semantic analysis)
    paper1.md .. paper3.md plain-text renderings of the papers
    markscheme_paper1.md   marking scheme for paper 1
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "examples" / "synthetic_inputs"

SUBJECT = "Introductory Physics"
LO = {
    "U1": "U1 Distinguish scalar and vector quantities and use SI units",
    "K1": "K1 Use the equations of uniformly accelerated motion",
    "K2": "K2 Interpret motion data in tables and graphs",
    "K3": "K3 Analyse projectile motion with independent horizontal and vertical components",
    "F1": "F1 Apply Newton's second law F = ma",
    "F2": "F2 Apply Hooke's law F = kx",
    "F3": "F3 Explain motion using Newton's first law",
    "E1": "E1 Calculate gravitational potential and kinetic energy",
    "E2": "E2 Calculate power and efficiency",
    "M1": "M1 Apply conservation of momentum",
    "W1": "W1 Use the wave equation v = f λ",
    "W2": "W2 Describe and calculate refraction of light",
    "C1": "C1 Apply Ohm's law to series circuits",
    "C2": "C2 Relate charge, current, potential difference and power",
}

QUESTIONS = []
ANNOTATIONS = {}


def g(symbol, value, unit, description, role=None):
    d = {"symbol": symbol, "value": value, "unit": unit, "description": description}
    if role:
        d["role"] = role
    return d


def pts(*items):
    out = []
    for it in items:
        desc, marks = it[0], it[1]
        p = {"description": desc, "marks": marks}
        if len(it) > 2:
            p["part"] = it[2]
        out.append(p)
    return out


def add(qid, paper, section, topic, subtopic, qtype, marks, text, *, los, cognitive, given=None, parts=None, options=None,
        answer_key=None, final_answer=None, worked=None, points=None, constraints=None, table=None, verification=None,
        required_output=None, diagram=None, ann=None, accept_rule=None):
    q = {
        "id": qid,
        "source": {"document": f"Synthetic Physics Paper {paper}", "page": 1 if section == "A" else 2, "section": section},
        "subject": SUBJECT,
        "topic": topic,
        "subtopic": subtopic,
        "text": text,
        "question_type": qtype,
        "marks": marks,
        "section": section,
        "learning_objectives": [LO[x] for x in los],
        "cognitive_level": cognitive,
        "given": given or [],
        "required_output": required_output,
        "constraints": constraints or [],
        "language": "en",
        "marking": {
            "scheme_available": True,
            "final_answer": final_answer,
            "answer_key": answer_key,
            "worked_solution": worked,
            "points": points or [],
            "accept_rule": accept_rule,
        },
        "extraction_confidence": "high",
        "evidence": [{"document": f"Synthetic Physics Paper {paper}", "page": 1 if section == "A" else 2, "quote": text[:120]}],
        "provenance": {"cognitive_level": "inferred", "topic": "inferred", "subtopic": "inferred", "learning_objectives": "inferred"},
    }
    if parts:
        q["parts"] = [{"label": l, "text": t, "marks": m} for l, t, m in parts]
    if options:
        q["options"] = [{"key": k, "text": t} for k, t in options]
    if table:
        q["table"] = table
    if diagram:
        q["diagram_description"] = diagram
    if verification:
        q["extensions"] = {"verification": verification}
    QUESTIONS.append(q)
    if ann:
        ANNOTATIONS[qid] = ann


def steps(*types, descriptions=None, edges=None):
    s = [{"id": f"s{i}", "type": t, **({"description": descriptions[i - 1]} if descriptions else {})} for i, t in enumerate(types, 1)]
    e = edges if edges is not None else [[f"s{i}", f"s{i + 1}"] for i in range(1, len(types))]
    return {"steps": s, "edges": e}


def ann(primary, *, secondary=(), prereq=(), reasoning, rep=("verbal",), context=None, explicit=(), implicit=(), boundary=(), math=1, answer=None):
    a = {
        "knowledge": {"primary_concept": primary, "secondary_concepts": list(secondary), "prerequisites": list(prereq)},
        "reasoning": reasoning,
        "representation": {"input": list(rep), "output": ["numeric"] if answer in (None, "numeric") else [], "context": context},
        "constraints": {"explicit": list(explicit), "implicit": list(implicit), "boundary": list(boundary)},
        "assessment": {"difficulty_features": {"math_complexity": math}},
    }
    if answer:
        a["assessment"]["answer_type"] = answer
    return a


def num(expr, variables, value, unit, **extra):
    v = {"kind": "numeric", "expression": expr, "variables": variables, "claimed_value": value, "claimed_unit": unit, "answer_uniqueness": "unique"}
    v.update(extra)
    return v


# ============================================================== PAPER 1 (30)
add("p1-a1", 1, "A", "Kinematics", "Scalars and vectors", "multiple_choice", 1,
    "Which of the following quantities is a vector?",
    los=["U1"], cognitive="recall",
    options=[("A", "Speed"), ("B", "Distance"), ("C", "Displacement"), ("D", "Time")],
    answer_key="C", final_answer="Displacement", points=pts(("C (displacement)", 1)),
    ann=ann("vector quantity", prereq=["scalar quantity"], reasoning=steps("recall_fact"), context="abstract", math=0, answer="choice"))

add("p1-a2", 1, "A", "Kinematics", "Uniform acceleration", "calculation", 2,
    "A cyclist accelerates uniformly from rest to a speed of 8.0 m/s in 4.0 s. Calculate the acceleration of the cyclist.",
    los=["K1"], cognitive="application",
    given=[g("v", 8.0, "m/s", "final speed"), g("t", 4.0, "s", "time taken")],
    required_output="acceleration a in m/s^2",
    final_answer="2.0 m/s²", worked="a = (v − u)/t = (8.0 − 0)/4.0 = 2.0 m/s²",
    points=pts(("Uses a = (v − u)/t with u = 0", 1), ("2.0 m/s²", 1)),
    verification=num("v/t", {"v": 8.0, "t": 4.0}, 2.0, "m/s^2"),
    ann=ann("uniform acceleration", secondary=["velocity"], prereq=["velocity"], context="cycling",
            reasoning=steps("read_given", "select_relation", "apply_mathematics", "derive_result"), math=1))

add("p1-a3", 1, "A", "Forces", "Newton's second law", "calculation", 2,
    "A resultant force of 6.0 N acts on a trolley of mass 2.0 kg. Calculate the acceleration of the trolley.",
    los=["F1"], cognitive="application",
    given=[g("F", 6.0, "N", "resultant force"), g("m", 2.0, "kg", "mass of trolley")],
    required_output="acceleration a in m/s^2",
    final_answer="3.0 m/s²", worked="a = F/m = 6.0/2.0 = 3.0 m/s²",
    points=pts(("a = F/m", 1), ("3.0 m/s²", 1)),
    verification=num("F/m", {"F": 6.0, "m": 2.0}, 3.0, "m/s^2"),
    ann=ann("Newton's second law", secondary=["acceleration"], prereq=["force", "mass"], context="laboratory trolley",
            reasoning=steps("read_given", "select_relation", "apply_mathematics", "derive_result"), math=1))

add("p1-a4", 1, "A", "Energy", "Power", "calculation", 2,
    "A lamp transfers 120 J of energy in 4.0 s. Calculate the power of the lamp.",
    los=["E2"], cognitive="application",
    given=[g("E", 120, "J", "energy transferred"), g("t", 4.0, "s", "time")],
    required_output="power P in W",
    final_answer="30 W", worked="P = E/t = 120/4.0 = 30 W",
    points=pts(("P = E/t", 1), ("30 W", 1)),
    verification=num("E/t", {"E": 120, "t": 4.0}, 30, "W"),
    ann=ann("power", secondary=["energy transfer"], prereq=["energy"], context="household lamp",
            reasoning=steps("read_given", "select_relation", "apply_mathematics", "derive_result"), math=1))

add("p1-a5", 1, "A", "Waves", "Wave equation", "multiple_choice", 1,
    "A wave has a frequency of 50 Hz and a wavelength of 2.0 m. What is the speed of the wave?",
    los=["W1"], cognitive="application",
    given=[g("f", 50, "Hz", "frequency"), g("lam", 2.0, "m", "wavelength")],
    options=[("A", "25 m/s"), ("B", "52 m/s"), ("C", "100 m/s"), ("D", "0.04 m/s")],
    answer_key="C", final_answer="100 m/s", points=pts(("C", 1)),
    verification=num("f*lam", {"f": 50, "lam": 2.0}, 100, "m/s"),
    ann=ann("wave equation", secondary=["frequency", "wavelength"], prereq=["frequency"], context="abstract",
            reasoning=steps("read_given", "select_relation", "apply_mathematics"), math=1, answer="choice"))

add("p1-a6", 1, "A", "Electricity", "Ohm's law", "calculation", 2,
    "A current of 0.50 A flows through a 12 Ω resistor. Calculate the potential difference across the resistor.",
    los=["C1"], cognitive="application",
    given=[g("I", 0.50, "A", "current"), g("R", 12, "ohm", "resistance")],
    required_output="potential difference V in V",
    final_answer="6.0 V", worked="V = IR = 0.50 × 12 = 6.0 V",
    points=pts(("V = IR", 1), ("6.0 V", 1)),
    verification=num("I*R", {"I": 0.50, "R": 12}, 6.0, "V"),
    ann=ann("Ohm's law", secondary=["resistance"], prereq=["current", "potential difference"], context="circuit",
            reasoning=steps("read_given", "select_relation", "apply_mathematics", "derive_result"), math=1))

add("p1-b1", 1, "B", "Kinematics", "Stopping distance", "mixed", 7,
    "A car travelling at 20 m/s brakes with uniform deceleration and comes to rest in a distance of 50 m.",
    los=["K1", "F3"], cognitive="multi_step_reasoning",
    given=[g("u", 20, "m/s", "initial speed"), g("s", 50, "m", "braking distance")],
    parts=[("a", "Calculate the magnitude of the deceleration of the car.", 3),
           ("b", "Calculate the time taken for the car to stop.", 2),
           ("c", "Explain why the braking distance would be larger on a wet road.", 2)],
    constraints=[{"text": "deceleration is uniform", "kind": "explicit"}, {"text": "the car comes to rest (v = 0)", "kind": "boundary"}],
    final_answer="(a) 4.0 m/s² (b) 5.0 s (c) less friction, so smaller decelerating force",
    worked="(a) v² = u² − 2as ⇒ a = u²/(2s) = 400/100 = 4.0 m/s². (b) t = u/a = 20/4.0 = 5.0 s. (c) Wet road reduces friction between tyres and road, so the maximum decelerating force and deceleration are smaller; the car travels further.",
    points=pts(("Selects v² = u² − 2as with v = 0", 1, "a"), ("Rearranges for a", 1, "a"), ("4.0 m/s²", 1, "a"),
               ("t = u/a or equivalent", 1, "b"), ("5.0 s", 1, "b"),
               ("Less friction / grip on wet road", 1, "c"), ("So smaller deceleration and greater distance", 1, "c")),
    verification=num("u**2/(2*s)", {"u": 20, "s": 50}, 4.0, "m/s^2", domain=[{"var": "result", "min": 0}]),
    ann=ann("uniformly accelerated motion", secondary=["friction", "stopping distance"], prereq=["acceleration", "velocity"], context="road transport",
            reasoning=steps("read_given", "identify_constraint", "select_relation", "apply_mathematics", "derive_result", "select_relation", "derive_result", "justify",
                            edges=[["s1", "s2"], ["s2", "s3"], ["s3", "s4"], ["s4", "s5"], ["s5", "s6"], ["s6", "s7"], ["s2", "s8"]]),
            explicit=["deceleration is uniform"], boundary=["final velocity is zero"], math=2))

add("p1-b2", 1, "B", "Energy", "Energy conservation", "mixed", 7,
    "A ball of mass 0.50 kg is dropped from rest from a height of 3.2 m. Air resistance is negligible. Take g = 9.8 m/s².",
    los=["E1"], cognitive="multi_step_reasoning",
    given=[g("m", 0.50, "kg", "mass"), g("h", 3.2, "m", "height"), g("g", 9.8, "m/s^2", "gravitational field strength", role="constant")],
    parts=[("a", "Calculate the gravitational potential energy lost by the ball as it falls to the ground.", 2),
           ("b", "Calculate the speed of the ball just before it hits the ground.", 3),
           ("c", "Explain how the speed just before impact would change if air resistance were not negligible.", 2)],
    constraints=[{"text": "air resistance is negligible", "kind": "explicit"}, {"text": "released from rest", "kind": "boundary"}],
    final_answer="(a) 15.7 J (b) 7.9 m/s (c) lower speed: some energy transferred to the surroundings",
    worked="(a) ΔEp = mgh = 0.50 × 9.8 × 3.2 = 15.68 ≈ 15.7 J. (b) ½mv² = mgh ⇒ v = √(2gh) = √62.72 = 7.9 m/s. (c) Work done against air resistance transfers energy to the surroundings, so less kinetic energy and a lower speed.",
    points=pts(("ΔEp = mgh", 1, "a"), ("15.7 J", 1, "a"), ("Equates kinetic energy gained to potential energy lost", 1, "b"), ("v = √(2gh)", 1, "b"), ("7.9 m/s", 1, "b"),
               ("Work done against air resistance", 1, "c"), ("Less kinetic energy so lower speed", 1, "c")),
    verification=num("m*g*h", {"m": 0.50, "g": 9.8, "h": 3.2}, 15.68, "J"),
    ann=ann("conservation of energy", secondary=["gravitational potential energy", "kinetic energy"], prereq=["energy stores", "work"], context="dropped ball",
            reasoning=steps("read_given", "select_relation", "apply_mathematics", "construct_model", "apply_mathematics", "derive_result", "interpret_result"),
            explicit=["air resistance is negligible"], boundary=["released from rest"], math=2))

add("p1-b3", 1, "B", "Electricity", "Series circuits", "calculation", 6,
    "A 4.0 Ω resistor and a 6.0 Ω resistor are connected in series with a 12 V battery of negligible internal resistance.",
    los=["C1"], cognitive="multi_step_reasoning",
    given=[g("R1", 4.0, "ohm", "first resistance"), g("R2", 6.0, "ohm", "second resistance"), g("V", 12, "V", "battery potential difference")],
    parts=[("a", "Calculate the total resistance of the circuit.", 1),
           ("b", "Calculate the current in the circuit.", 2),
           ("c", "Calculate the potential difference across the 6.0 Ω resistor.", 3)],
    constraints=[{"text": "battery has negligible internal resistance", "kind": "explicit"}],
    final_answer="(a) 10 Ω (b) 1.2 A (c) 7.2 V",
    worked="(a) R = 4.0 + 6.0 = 10 Ω. (b) I = V/R = 12/10 = 1.2 A. (c) V2 = IR2 = 1.2 × 6.0 = 7.2 V.",
    points=pts(("10 Ω", 1, "a"), ("I = V/R", 1, "b"), ("1.2 A", 1, "b"), ("Same current in series", 1, "c"), ("V = IR2", 1, "c"), ("7.2 V", 1, "c")),
    verification=num("V*R2/(R1+R2)", {"V": 12, "R1": 4.0, "R2": 6.0}, 7.2, "V"),
    ann=ann("series circuit", secondary=["Ohm's law"], prereq=["resistance", "current"], context="circuit",
            reasoning=steps("read_given", "construct_model", "apply_mathematics", "select_relation", "apply_mathematics", "derive_result"),
            explicit=["negligible internal resistance"], math=1))

# ============================================================== PAPER 2 (30)
add("p2-a1", 2, "A", "Momentum", "Momentum", "multiple_choice", 1,
    "Which of the following is a correct unit for momentum?",
    los=["U1", "M1"], cognitive="recall",
    options=[("A", "kg m/s"), ("B", "kg m/s²"), ("C", "N/s"), ("D", "J s")],
    answer_key="A", final_answer="kg m/s", points=pts(("A", 1)),
    ann=ann("momentum", prereq=["mass", "velocity"], reasoning=steps("recall_fact"), context="abstract", math=0, answer="choice"))

add("p2-a2", 2, "A", "Momentum", "Momentum", "calculation", 2,
    "A car of mass 1200 kg is moving at 15 m/s. Calculate the momentum of the car.",
    los=["M1"], cognitive="application",
    given=[g("m", 1200, "kg", "mass"), g("v", 15, "m/s", "velocity")],
    required_output="momentum p in kg m/s",
    final_answer="18000 kg m/s", worked="p = mv = 1200 × 15 = 18 000 kg m/s",
    points=pts(("p = mv", 1), ("18 000 kg m/s", 1)),
    verification=num("m*v", {"m": 1200, "v": 15}, 18000, "kg m/s"),
    ann=ann("momentum", secondary=["velocity"], prereq=["mass", "velocity"], context="road transport",
            reasoning=steps("read_given", "select_relation", "apply_mathematics", "derive_result"), math=1))

add("p2-a3", 2, "A", "Forces", "Hooke's law", "calculation", 2,
    "A spring with spring constant 40 N/m is extended by 0.15 m. Calculate the force applied to the spring.",
    los=["F2"], cognitive="application",
    given=[g("k", 40, "N/m", "spring constant"), g("x", 0.15, "m", "extension")],
    constraints=[{"text": "the spring obeys Hooke's law (limit of proportionality not exceeded)", "kind": "explicit"}],
    required_output="force F in N",
    final_answer="6.0 N", worked="F = kx = 40 × 0.15 = 6.0 N",
    points=pts(("F = kx", 1), ("6.0 N", 1)),
    verification=num("k*x", {"k": 40, "x": 0.15}, 6.0, "N"),
    ann=ann("Hooke's law", secondary=["elastic deformation"], prereq=["force"], context="spring",
            reasoning=steps("read_given", "select_relation", "apply_mathematics", "derive_result"), explicit=["limit of proportionality not exceeded"], math=1))

add("p2-a4", 2, "A", "Waves", "Wave equation", "multiple_choice", 1,
    "A sound wave travels at 340 m/s and has a frequency of 170 Hz. What is its wavelength?",
    los=["W1"], cognitive="application",
    given=[g("v", 340, "m/s", "wave speed"), g("f", 170, "Hz", "frequency")],
    options=[("A", "0.50 m"), ("B", "2.0 m"), ("C", "510 m"), ("D", "57 800 m")],
    answer_key="B", final_answer="2.0 m", points=pts(("B", 1)),
    verification=num("v/f", {"v": 340, "f": 170}, 2.0, "m"),
    ann=ann("wave equation", secondary=["sound"], prereq=["frequency"], context="sound",
            reasoning=steps("read_given", "select_relation", "apply_mathematics"), math=1, answer="choice"))

add("p2-a5", 2, "A", "Electricity", "Current and charge", "calculation", 2,
    "A charge of 30 C flows through a lamp in 60 s. Calculate the current in the lamp.",
    los=["C2"], cognitive="application",
    given=[g("Q", 30, "C", "charge"), g("t", 60, "s", "time")],
    required_output="current I in A",
    final_answer="0.50 A", worked="I = Q/t = 30/60 = 0.50 A",
    points=pts(("I = Q/t", 1), ("0.50 A", 1)),
    verification=num("Q/t", {"Q": 30, "t": 60}, 0.5, "A"),
    ann=ann("electric current", secondary=["charge"], prereq=["charge"], context="household lamp",
            reasoning=steps("read_given", "select_relation", "apply_mathematics", "derive_result"), math=1))

add("p2-a6", 2, "A", "Forces", "Newton's first law", "short_answer", 2,
    "A puck slides across a frictionless horizontal surface. Explain why it continues to move at constant velocity.",
    los=["F3"], cognitive="interpretation",
    constraints=[{"text": "surface is frictionless", "kind": "explicit"}],
    final_answer="No resultant force acts, so by Newton's first law the velocity does not change.",
    points=pts(("No resultant (unbalanced) force acts on the puck", 1), ("So velocity is unchanged (Newton's first law)", 1)),
    ann=ann("Newton's first law", secondary=["resultant force"], prereq=["force"], context="ice hockey",
            reasoning=steps("identify_constraint", "recall_fact", "justify"), explicit=["frictionless surface"], math=0, answer="short_text"))

add("p2-b1", 2, "B", "Momentum", "Collisions", "mixed", 8,
    "A trolley of mass 2.0 kg moving at 3.0 m/s collides with a stationary trolley of mass 1.0 kg. The trolleys stick together.",
    los=["M1", "E1"], cognitive="multi_step_reasoning",
    given=[g("m1", 2.0, "kg", "mass of moving trolley"), g("u1", 3.0, "m/s", "initial velocity"), g("m2", 1.0, "kg", "mass of stationary trolley")],
    parts=[("a", "Calculate the total momentum before the collision.", 2),
           ("b", "Calculate the velocity of the trolleys immediately after the collision.", 3),
           ("c", "Calculate the kinetic energy lost in the collision.", 3)],
    constraints=[{"text": "no external horizontal forces act", "kind": "implicit"}, {"text": "trolleys stick together", "kind": "explicit"}],
    final_answer="(a) 6.0 kg m/s (b) 2.0 m/s (c) 3.0 J",
    worked="(a) p = 2.0 × 3.0 = 6.0 kg m/s. (b) v = 6.0/3.0 = 2.0 m/s. (c) Ek before = ½ × 2.0 × 3.0² = 9.0 J; after = ½ × 3.0 × 2.0² = 6.0 J; lost 3.0 J.",
    points=pts(("p = mv", 1, "a"), ("6.0 kg m/s", 1, "a"), ("Momentum conserved", 1, "b"), ("Combined mass 3.0 kg", 1, "b"), ("2.0 m/s", 1, "b"),
               ("Ek before 9.0 J", 1, "c"), ("Ek after 6.0 J", 1, "c"), ("3.0 J lost", 1, "c")),
    verification=num("m1*u1", {"m1": 2.0, "u1": 3.0}, 6.0, "kg m/s"),
    ann=ann("conservation of momentum", secondary=["kinetic energy", "inelastic collision"], prereq=["momentum"], context="laboratory trolley",
            reasoning=steps("read_given", "select_relation", "apply_mathematics", "construct_model", "derive_result", "select_relation", "apply_mathematics", "compare",
                            edges=[["s1", "s2"], ["s2", "s3"], ["s3", "s4"], ["s4", "s5"], ["s5", "s6"], ["s1", "s6"], ["s6", "s7"], ["s7", "s8"]]),
            explicit=["trolleys stick together"], implicit=["no external horizontal force"], math=2))

add("p2-b2", 2, "B", "Kinematics", "Motion data", "data_interpretation", 6,
    "The table shows the velocity of a sprinter at different times after the start of a race.",
    los=["K2", "K1"], cognitive="interpretation",
    given=[g("v4", 6.0, "m/s", "velocity at 4.0 s"), g("t4", 4.0, "s", "time of acceleration"), g("t6", 6.0, "s", "total time")],
    table={"caption": "Velocity of the sprinter", "columns": ["t / s", "v / m s⁻¹"], "rows": [[0, 0], [2.0, 3.0], [4.0, 6.0], [6.0, 6.0]]},
    parts=[("a", "Calculate the acceleration of the sprinter during the first 4.0 s.", 2),
           ("b", "Calculate the distance travelled in the first 6.0 s.", 3),
           ("c", "Describe the motion of the sprinter between 4.0 s and 6.0 s.", 1)],
    final_answer="(a) 1.5 m/s² (b) 24 m (c) constant velocity of 6.0 m/s",
    worked="(a) a = 6.0/4.0 = 1.5 m/s². (b) Distance = ½ × 4.0 × 6.0 + 6.0 × 2.0 = 12 + 12 = 24 m. (c) Constant velocity (zero acceleration).",
    points=pts(("a = Δv/Δt", 1, "a"), ("1.5 m/s²", 1, "a"), ("Distance during acceleration 12 m", 1, "b"), ("Distance at constant speed 12 m", 1, "b"), ("24 m", 1, "b"), ("Constant velocity", 1, "c")),
    verification=num("0.5*t4*v4 + v4*(t6-t4)", {"t4": 4.0, "v4": 6.0, "t6": 6.0}, 24, "m"),
    ann=ann("motion data interpretation", secondary=["uniformly accelerated motion"], prereq=["velocity", "acceleration"], context="sports and athletics",
            reasoning=steps("read_representation", "select_relation", "apply_mathematics", "construct_model", "apply_mathematics", "derive_result", "interpret_result"),
            rep=("verbal", "table"), math=2))

add("p2-b3", 2, "B", "Electricity", "Electrical power", "mixed", 6,
    "An electric kettle is connected to a 230 V mains supply and draws a current of 8.0 A.",
    los=["C2", "E2"], cognitive="application",
    given=[g("V", 230, "V", "supply voltage"), g("I", 8.0, "A", "current"), g("t", 120, "s", "heating time")],
    parts=[("a", "Calculate the power of the kettle.", 2),
           ("b", "Calculate the energy transferred by the kettle in 120 s.", 2),
           ("c", "Suggest why the kettle cable is thicker than the cable for a lamp.", 2)],
    final_answer="(a) 1840 W (b) 2.2 × 10^5 J (c) larger current; thicker cable has lower resistance so less heating",
    worked="(a) P = VI = 230 × 8.0 = 1840 W. (b) E = Pt = 1840 × 120 = 220 800 J ≈ 2.2 × 10⁵ J. (c) Large current; thick cable has lower resistance so it does not overheat.",
    points=pts(("P = VI", 1, "a"), ("1840 W", 1, "a"), ("E = Pt", 1, "b"), ("2.2 × 10⁵ J", 1, "b"), ("Larger current", 1, "c"), ("Lower resistance so less heating", 1, "c")),
    verification=num("V*I", {"V": 230, "I": 8.0}, 1840, "W"),
    ann=ann("electrical power", secondary=["energy transfer"], prereq=["current", "potential difference"], context="household appliances",
            reasoning=steps("read_given", "select_relation", "apply_mathematics", "select_relation", "apply_mathematics", "justify",
                            edges=[["s1", "s2"], ["s2", "s3"], ["s3", "s4"], ["s4", "s5"], ["s1", "s6"]]), math=1))

# ============================================================== PAPER 3 (32)
add("p3-a1", 3, "A", "Energy", "Power", "multiple_choice", 1,
    "Which of the following is the SI unit of power?",
    los=["U1", "E2"], cognitive="recall",
    options=[("A", "joule"), ("B", "newton"), ("C", "watt"), ("D", "pascal")],
    answer_key="C", final_answer="watt", points=pts(("C", 1)),
    ann=ann("power", prereq=["energy"], reasoning=steps("recall_fact"), context="abstract", math=0, answer="choice"))

add("p3-a2", 3, "A", "Energy", "Gravitational potential energy", "calculation", 2,
    "A climber of mass 60 kg climbs a vertical height of 12 m. Calculate the gain in gravitational potential energy of the climber. Take g = 9.8 m/s².",
    los=["E1"], cognitive="application",
    given=[g("m", 60, "kg", "mass"), g("h", 12, "m", "height gained"), g("g", 9.8, "m/s^2", "gravitational field strength", role="constant")],
    required_output="gain in GPE in J",
    final_answer="7056 J (7.1 kJ)", worked="ΔEp = mgh = 60 × 9.8 × 12 = 7056 J ≈ 7.1 kJ",
    points=pts(("ΔEp = mgh", 1), ("7056 J / 7.1 kJ", 1)),
    verification=num("m*g*h", {"m": 60, "g": 9.8, "h": 12}, 7056, "J"),
    ann=ann("gravitational potential energy", prereq=["weight"], context="climbing",
            reasoning=steps("read_given", "select_relation", "apply_mathematics", "derive_result"), math=1))

add("p3-a3", 3, "A", "Kinematics", "Projectile motion", "calculation", 3,
    "A ball rolls off the edge of a horizontal table 1.8 m above the floor. Air resistance is negligible. Calculate the time taken for the ball to reach the floor. Take g = 9.8 m/s².",
    los=["K3", "K1"], cognitive="multi_step_reasoning",
    given=[g("h", 1.8, "m", "height of table"), g("g", 9.8, "m/s^2", "gravitational field strength", role="constant")],
    constraints=[{"text": "air resistance is negligible", "kind": "explicit"}, {"text": "initial vertical velocity is zero", "kind": "boundary"}],
    required_output="time t in s",
    final_answer="0.61 s", worked="Vertical motion independent: h = ½gt² ⇒ t = √(2h/g) = √(3.6/9.8) = 0.61 s",
    points=pts(("Vertical initial velocity is zero / motions independent", 1), ("h = ½gt²", 1), ("0.61 s", 1)),
    verification=num("sqrt(2*h/g)", {"h": 1.8, "g": 9.8}, 0.606, "s"),
    ann=ann("projectile motion", secondary=["uniformly accelerated motion"], prereq=["acceleration", "vector components"], context="table-top experiment",
            reasoning=steps("read_given", "identify_constraint", "construct_model", "select_relation", "apply_mathematics", "derive_result"),
            explicit=["air resistance negligible"], boundary=["initial vertical velocity zero"], math=3))

add("p3-a4", 3, "A", "Waves", "Wave equation", "calculation", 2,
    "A wave on a stretched string travels at 12 m/s and has a wavelength of 0.40 m. Calculate the frequency of the wave.",
    los=["W1"], cognitive="application",
    given=[g("v", 12, "m/s", "wave speed"), g("lam", 0.40, "m", "wavelength")],
    required_output="frequency f in Hz",
    final_answer="30 Hz", worked="f = v/λ = 12/0.40 = 30 Hz",
    points=pts(("f = v/λ", 1), ("30 Hz", 1)),
    verification=num("v/lam", {"v": 12, "lam": 0.40}, 30, "Hz"),
    ann=ann("wave equation", prereq=["frequency", "wavelength"], context="music and acoustics",
            reasoning=steps("read_given", "select_relation", "apply_mathematics", "derive_result"), math=1))

add("p3-a5", 3, "A", "Electricity", "Ohm's law", "calculation", 2,
    "The potential difference across a 220 Ω resistor is 11 V. Calculate the current in the resistor.",
    los=["C1"], cognitive="application",
    given=[g("V", 11, "V", "potential difference"), g("R", 220, "ohm", "resistance")],
    required_output="current I in A",
    final_answer="0.050 A", worked="I = V/R = 11/220 = 0.050 A",
    points=pts(("I = V/R", 1), ("0.050 A", 1)),
    verification=num("V/R", {"V": 11, "R": 220}, 0.05, "A"),
    ann=ann("Ohm's law", prereq=["current", "potential difference"], context="circuit",
            reasoning=steps("read_given", "select_relation", "apply_mathematics", "derive_result"), math=1))

# Deliberately ambiguous source question: refers to a diagram that is not supplied and omits the angle and friction.
add("p3-a6", 3, "A", "Forces", "Inclined planes", "calculation", 2,
    "A block slides down the slope shown in the diagram. Calculate its acceleration.",
    los=["F1"], cognitive="application",
    given=[g("m", 3.0, "kg", "mass of block")],
    required_output="acceleration in m/s^2",
    final_answer=None, worked=None,
    points=pts(("Resolves weight along slope", 1), ("Correct acceleration", 1)),
    verification=num("g*sin(theta)", {"g": 9.8, "theta": 0.52}, 4.9, "m/s^2"),
    ann=ann("Newton's second law", secondary=["components of weight"], prereq=["force", "trigonometry"], context="inclined plane",
            reasoning=steps("read_representation", "construct_model", "apply_mathematics", "derive_result"), rep=("verbal", "diagram"), math=2))

add("p3-b1", 3, "B", "Forces", "Newton's second law", "mixed", 7,
    "A lift of total mass 900 kg accelerates upwards at 1.5 m/s². Take g = 9.8 m/s².",
    los=["F1", "F3"], cognitive="multi_step_reasoning",
    given=[g("m", 900, "kg", "mass of lift"), g("a", 1.5, "m/s^2", "upward acceleration"), g("g", 9.8, "m/s^2", "gravitational field strength", role="constant")],
    parts=[("a", "Calculate the weight of the lift.", 1),
           ("b", "Calculate the tension in the lift cable.", 3),
           ("c", "Explain why the tension is smaller when the lift moves upwards at constant speed.", 3)],
    constraints=[{"text": "acceleration is upward and uniform", "kind": "explicit"}],
    final_answer="(a) 8820 N (b) 1.0 × 10^4 N (10 170 N) (c) at constant speed the resultant force is zero, so tension equals weight",
    worked="(a) W = mg = 900 × 9.8 = 8820 N. (b) T − mg = ma ⇒ T = m(g + a) = 900 × 11.3 = 10 170 N. (c) Constant speed ⇒ zero acceleration ⇒ zero resultant force ⇒ T = W = 8820 N, which is smaller.",
    points=pts(("8820 N", 1, "a"), ("Resultant force T − mg = ma", 1, "b"), ("T = m(g + a)", 1, "b"), ("10 170 N", 1, "b"),
               ("Constant speed means zero acceleration", 1, "c"), ("Resultant force is zero", 1, "c"), ("So tension equals weight, smaller than before", 1, "c")),
    verification=num("m*g", {"m": 900, "g": 9.8}, 8820, "N"),
    ann=ann("Newton's second law", secondary=["weight", "Newton's first law"], prereq=["force", "acceleration"], context="building lift",
            reasoning=steps("read_given", "select_relation", "apply_mathematics", "construct_model", "apply_mathematics", "derive_result", "compare", "justify"),
            explicit=["acceleration upward and uniform"], math=2))

add("p3-b2", 3, "B", "Energy", "Efficiency", "calculation", 7,
    "An electric motor lifts a load of mass 25 kg through a vertical height of 4.0 m in 8.0 s. The input power to the motor is 200 W. Take g = 9.8 m/s².",
    los=["E1", "E2"], cognitive="multi_step_reasoning",
    given=[g("m", 25, "kg", "mass of load"), g("h", 4.0, "m", "height"), g("t", 8.0, "s", "time"), g("P", 200, "W", "input power"), g("g", 9.8, "m/s^2", "gravitational field strength", role="constant")],
    parts=[("a", "Calculate the useful energy transferred to the load.", 2),
           ("b", "Calculate the total energy supplied to the motor.", 2),
           ("c", "Calculate the efficiency of the motor.", 3)],
    final_answer="(a) 980 J (b) 1600 J (c) 0.61 (61 %)",
    worked="(a) ΔEp = mgh = 25 × 9.8 × 4.0 = 980 J. (b) E = Pt = 200 × 8.0 = 1600 J. (c) efficiency = 980/1600 = 0.61 (61 %).",
    points=pts(("mgh", 1, "a"), ("980 J", 1, "a"), ("E = Pt", 1, "b"), ("1600 J", 1, "b"), ("efficiency = useful/total", 1, "c"), ("Uses 980 and 1600", 1, "c"), ("0.61 or 61 %", 1, "c")),
    verification=num("m*g*h", {"m": 25, "g": 9.8, "h": 4.0}, 980, "J"),
    ann=ann("efficiency", secondary=["gravitational potential energy", "power"], prereq=["energy", "power"], context="construction and engineering",
            reasoning=steps("read_given", "select_relation", "apply_mathematics", "select_relation", "apply_mathematics", "construct_model", "derive_result",
                            edges=[["s1", "s2"], ["s2", "s3"], ["s1", "s4"], ["s4", "s5"], ["s3", "s6"], ["s5", "s6"], ["s6", "s7"]]), math=2))

add("p3-b3", 3, "B", "Waves", "Refraction", "mixed", 6,
    "Light travels from air into a glass block of refractive index 1.5. The speed of light in air is 3.0 × 10^8 m/s.",
    los=["W2", "W1"], cognitive="interpretation",
    given=[g("c", 3.0e8, "m/s", "speed of light in air"), g("n", 1.5, "1", "refractive index (dimensionless)")],
    parts=[("a", "Calculate the speed of light in the glass.", 2),
           ("b", "Explain why a ray entering the glass at an angle changes direction.", 2),
           ("c", "State what happens to the frequency of the light as it enters the glass, and give a reason.", 2)],
    final_answer="(a) 2.0 × 10^8 m/s (b) speed decreases on entering the denser medium (c) unchanged; set by the source",
    worked="(a) v = c/n = 3.0 × 10⁸/1.5 = 2.0 × 10⁸ m/s. (b) The light slows down; one side of the wavefront slows first so the direction changes. (c) Frequency unchanged: it is determined by the source.",
    points=pts(("v = c/n", 1, "a"), ("2.0 × 10⁸ m/s", 1, "a"), ("Speed decreases in glass", 1, "b"), ("Wavefront slows unevenly, so direction changes", 1, "b"), ("Frequency unchanged", 1, "c"), ("Determined by the source", 1, "c")),
    verification=num("c/n", {"c": 3.0e8, "n": 1.5}, 2.0e8, "m/s"),
    ann=ann("refraction", secondary=["wave speed"], prereq=["wave equation"], context="optics",
            reasoning=steps("read_given", "select_relation", "apply_mathematics", "recall_fact", "justify", "recall_fact", "justify",
                            edges=[["s1", "s2"], ["s2", "s3"], ["s3", "s4"], ["s4", "s5"], ["s3", "s6"], ["s6", "s7"]]), math=1))


def render_paper(paper: int) -> str:
    qs = [q for q in QUESTIONS if q["source"]["document"] == f"Synthetic Physics Paper {paper}"]
    total = sum(q["marks"] for q in qs)
    lines = [f"# Synthetic Physics Paper {paper}", "", f"Subject: {SUBJECT}", "",
             f"Total: {total} marks. Answer all questions. (Original synthetic material created for ExamDNA.)", ""]
    for section in ("A", "B"):
        sec_q = [q for q in qs if q["section"] == section]
        lines += [f"## Section {section}", ""]
        for i, q in enumerate(sec_q, 1):
            if q.get("parts"):
                lines.append(f"{i}. {q['text']}")
                for p in q["parts"]:
                    lines.append(f"({p['label']}) {p['text']} [{p['marks']} marks]")
            else:
                mk = "mark" if q["marks"] == 1 else "marks"
                lines.append(f"{i}. {q['text']} [{q['marks']} {mk}]")
            if q.get("table"):
                t = q["table"]
                lines.append("   " + " | ".join(t["columns"]))
                for r in t["rows"]:
                    lines.append("   " + " | ".join(str(c) for c in r))
            for o in q.get("options") or []:
                lines.append(f"   {o['key']}. {o['text']}")
            lines.append("")
    return "\n".join(lines)


def render_markscheme(paper: int) -> str:
    qs = [q for q in QUESTIONS if q["source"]["document"] == f"Synthetic Physics Paper {paper}"]
    lines = [f"# Marking Scheme — Synthetic Physics Paper {paper}", "", "Original synthetic material created for ExamDNA.", ""]
    for q in qs:
        m = q["marking"]
        lines.append(f"## {q['id']} ({q['marks']} marks)")
        lines.append("")
        if m.get("answer_key"):
            lines.append(f"Answer: **{m['answer_key']}** ({m['final_answer']})")
        elif m.get("final_answer"):
            lines.append(f"Answer: {m['final_answer']}")
        else:
            lines.append("Answer: not determinable from the information given (see examiner note).")
        for p in m["points"]:
            part = f"({p['part']}) " if p.get("part") else ""
            lines.append(f"- {part}{p['description']} [{p['marks']}]")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    bank = {
        "title": "Synthetic introductory physics papers (original, for demonstration)",
        "subject": SUBJECT,
        "source_documents": [
            {"name": f"Synthetic Physics Paper {i}", "kind": "exam", "paper_id": f"P{i}"} for i in (1, 2, 3)
        ] + [{"name": "Marking Scheme — Synthetic Physics Paper 1", "kind": "markscheme"},
             {"name": "Mini syllabus", "kind": "syllabus"}, {"name": "Teaching notes", "kind": "notes"}],
        "questions": QUESTIONS,
    }
    (OUT / "physics_bank.json").write_text(json.dumps(bank, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (OUT / "annotations.json").write_text(json.dumps({"annotations": ANNOTATIONS}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    for i in (1, 2, 3):
        (OUT / f"paper{i}.md").write_text(render_paper(i) + "\n", encoding="utf-8", newline="\n")
    (OUT / "markscheme_paper1.md").write_text(render_markscheme(1) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {len(QUESTIONS)} questions and {len(ANNOTATIONS)} annotations to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
