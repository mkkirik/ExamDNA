"""Write the demo candidates (the agent's Stage-B output) for the demo plan.

These candidates were authored during development by Claude acting as the
agent, following each mutation spec. They are stored as fixtures so the
deterministic pipeline can be demonstrated and tested without a model call.
Several are deliberately flawed first attempts ("-try1") to exercise rejection.

Usage: python tools/build_demo_candidates.py <workspace>
Reads <workspace>/mutation_plan.json, writes <workspace>/candidates.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_synthetic_dataset import LO, SUBJECT  # noqa: E402


def lin(*types, edges=None):
    steps = [{"id": f"s{i}", "type": t} for i, t in enumerate(types, 1)]
    return {"steps": steps, "edges": edges if edges is not None else [[f"s{i}", f"s{i + 1}"] for i in range(1, len(types))]}


def genome(qid, primary, *, secondary=(), prereq=(), los=(), reasoning, rep=("verbal",), context=None, explicit=(), implicit=(), boundary=(), math=1, answer="numeric"):
    return {
        "schema_version": "0.1.0",
        "genome_id": f"g-{qid}",
        "question_id": qid,
        "knowledge": {"primary_concept": primary, "secondary_concepts": list(secondary), "prerequisites": list(prereq), "learning_objectives": [LO[x] for x in los]},
        "reasoning": reasoning,
        "representation": {"input": list(rep), "output": ["numeric"] if answer == "numeric" else [], "context": context},
        "constraints": {"explicit": list(explicit), "implicit": list(implicit), "domain": [], "boundary": list(boundary), "units": []},
        "assessment": {"answer_type": answer, "difficulty_features": {"math_complexity": math}},
        "validation": {},
    }


def g(symbol, value, unit, description, role=None):
    d = {"symbol": symbol, "value": value, "unit": unit, "description": description}
    if role:
        d["role"] = role
    return d


def question(qid, topic, subtopic, qtype, marks, section, text, *, los, cognitive, given=(), parts=None, options=None, answer_key=None,
             final=None, worked=None, points=(), constraints=(), table=None, diagram=None, accept_rule=None):
    q = {
        "id": qid,
        "source": {"origin": "generated"},
        "subject": SUBJECT,
        "topic": topic,
        "subtopic": subtopic,
        "text": text,
        "question_type": qtype,
        "marks": marks,
        "section": section,
        "learning_objectives": [LO[x] for x in los],
        "cognitive_level": cognitive,
        "given": list(given),
        "constraints": list(constraints),
        "language": "en",
        "marking": {"scheme_available": True, "final_answer": final, "answer_key": answer_key, "worked_solution": worked,
                    "points": [dict(description=p[0], marks=p[1], **({"part": p[2]} if len(p) > 2 else {})) for p in points], "accept_rule": accept_rule},
        "provenance": {"text": "inferred"},
    }
    if parts:
        q["parts"] = [{"label": l, "text": t, "marks": m} for l, t, m in parts]
    if options:
        q["options"] = [{"key": k, "text": t} for k, t in options]
    if table:
        q["table"] = table
    if diagram:
        q["diagram_description"] = diagram
    return q


def num(expr, variables, value, unit, **extra):
    v = {"kind": "numeric", "expression": expr, "variables": variables, "claimed_value": value, "claimed_unit": unit, "answer_uniqueness": "unique"}
    v.update(extra)
    return v


def judge(skill=True, rationale="Same target concept and skill as the parent.", **extra):
    out = [{"property": "target_skill", "preserved": skill, "rationale": rationale}]
    for k, v in extra.items():
        out.append({"property": k, "preserved": v, "rationale": None})
    return out


def build(spec_for):
    C = []

    def cand(cid, parent, op, q, gnm, verification, judgements, summary):
        spec = spec_for(parent, op)
        C.append({"candidate_id": cid, "spec_id": spec, "parent_id": parent, "operator": op, "question": q, "genome": gnm,
                  "verification": verification, "invariant_judgements": judgements, "change_summary": summary})

    # p1-a2 representation verbal -> graph
    qid = "m-p1-a2-rep"
    cand("c01", "p1-a2", "representation",
         question(qid, "Kinematics", "Uniform acceleration", "calculation", 2, "A",
                  "The velocity–time graph for a skateboarder moving in a straight line is shown below. Use the graph to determine the acceleration of the skateboarder.",
                  los=["K1", "K2"], cognitive="application",
                  given=[g("v", 9.0, "m/s", "velocity at 5.0 s (read from graph)"), g("t", 5.0, "s", "time (read from graph)")],
                  diagram="Velocity–time graph: velocity v / m s⁻¹ on the vertical axis (0 to 10), time t / s on the horizontal axis (0 to 6). A straight line runs from (0 s, 0 m/s) to (5.0 s, 9.0 m/s).",
                  final="1.8 m/s²", worked="a = gradient = Δv/Δt = 9.0/5.0 = 1.8 m/s²",
                  points=[("Acceleration = gradient of v–t graph", 1), ("1.8 m/s²", 1)]),
         genome(qid, "uniform acceleration", secondary=["velocity", "gradient"], prereq=["velocity"], los=["K1", "K2"], context="skateboarding",
                reasoning=lin("read_representation", "select_relation", "apply_mathematics", "derive_result"), rep=("verbal", "graph"), math=1),
         num("v/t", {"v": 9.0, "t": 5.0}, 1.8, "m/s^2"), judge(), "Data now read from a v–t graph; acceleration found as the gradient.")

    # p1-a3 reasoning path: kinematics first, then F = ma
    qid = "m-p1-a3-path"
    cand("c02", "p1-a3", "reasoning_path",
         question(qid, "Forces", "Newton's second law", "calculation", 3, "A",
                  "A trolley of mass 2.0 kg is pulled from rest by a constant resultant force and reaches a speed of 1.5 m/s after 0.50 s. Calculate the resultant force on the trolley.",
                  los=["F1", "K1"], cognitive="multi_step_reasoning",
                  given=[g("m", 2.0, "kg", "mass"), g("v", 1.5, "m/s", "final speed"), g("t", 0.50, "s", "time")],
                  final="6.0 N", worked="a = v/t = 1.5/0.50 = 3.0 m/s²; F = ma = 2.0 × 3.0 = 6.0 N",
                  points=[("a = (v − u)/t", 1), ("F = ma", 1), ("6.0 N", 1)]),
         genome(qid, "Newton's second law", secondary=["acceleration", "uniform acceleration"], prereq=["force", "mass", "velocity"], los=["F1", "K1"], context="laboratory trolley",
                reasoning=lin("read_given", "select_relation", "apply_mathematics", "select_relation", "apply_mathematics", "derive_result"), math=1),
         num("m*v/t", {"m": 2.0, "v": 1.5, "t": 0.50}, 6.0, "N"), judge(), "Acceleration must first be found from motion data, then F = ma: a two-relation path instead of one.")

    # p1-a4 constraint add
    qid = "m-p1-a4-con"
    cand("c03", "p1-a4", "constraint",
         question(qid, "Energy", "Power", "calculation", 3, "A",
                  "A bedside lamp is rated at a maximum of 40 W. In a test it transfers 150 J of energy in 5.0 s. Calculate the power of the lamp and state whether it is operating within its rating.",
                  los=["E2"], cognitive="application",
                  given=[g("E", 150, "J", "energy transferred"), g("t", 5.0, "s", "time"), g("Pmax", 40, "W", "rated maximum power", role="data")],
                  constraints=[{"text": "power must not exceed the 40 W rating", "kind": "explicit"}],
                  final="30 W; within the 40 W rating", worked="P = E/t = 150/5.0 = 30 W, which is less than 40 W, so within rating.",
                  points=[("P = E/t", 1), ("30 W", 1), ("Compares with 40 W: within rating", 1)]),
         genome(qid, "power", secondary=["energy transfer", "power rating"], prereq=["energy"], los=["E2"], context="household lamp",
                reasoning=lin("read_given", "select_relation", "apply_mathematics", "derive_result", "compare"), explicit=["power must not exceed the 40 W rating"], math=1),
         num("E/t", {"E": 150, "t": 5.0}, 30, "W", domain=[{"var": "result", "min": 0, "max": 40}]), judge(), "Adds a power-rating constraint that the result must be checked against.")

    # p1-a6 surface — try1 is invalid (changes a given value), try2 valid
    qid = "m-p1-a6-surf"
    cand("c04-try1", "p1-a6", "surface",
         question(qid + "-t1", "Electricity", "Ohm's law", "calculation", 2, "A",
                  "Determine the potential difference across a 12 Ω resistor that carries a steady current of 0.40 A.",
                  los=["C1"], cognitive="application",
                  given=[g("I", 0.40, "A", "current"), g("R", 12, "ohm", "resistance")],
                  final="4.8 V", worked="V = IR = 0.40 × 12 = 4.8 V", points=[("V = IR", 1), ("4.8 V", 1)]),
         genome(qid + "-t1", "Ohm's law", secondary=["resistance"], prereq=["current", "potential difference"], los=["C1"], context="circuit",
                reasoning=lin("read_given", "select_relation", "apply_mathematics", "derive_result"), math=1),
         num("I*R", {"I": 0.40, "R": 12}, 4.8, "V"), judge(), "Concise rewording (first attempt).")
    cand("c04-try2", "p1-a6", "surface",
         question(qid, "Electricity", "Ohm's law", "calculation", 2, "A",
                  "Determine the potential difference across a 12 Ω resistor that carries a steady current of 0.50 A.",
                  los=["C1"], cognitive="application",
                  given=[g("I", 0.50, "A", "current"), g("R", 12, "ohm", "resistance")],
                  final="6.0 V", worked="V = IR = 0.50 × 12 = 6.0 V", points=[("V = IR", 1), ("6.0 V", 1)]),
         genome(qid, "Ohm's law", secondary=["resistance"], prereq=["current", "potential difference"], los=["C1"], context="circuit",
                reasoning=lin("read_given", "select_relation", "apply_mathematics", "derive_result"), math=1),
         num("I*R", {"I": 0.50, "R": 12}, 6.0, "V"), judge(), "Concise technical rewording; data, method and answer unchanged.")

    # p2-a2 difficulty up (require interpretation)
    qid = "m-p2-a2-diff"
    cand("c05", "p2-a2", "difficulty",
         question(qid, "Momentum", "Momentum", "calculation", 3, "A",
                  "A car of mass 1200 kg travels at 15 m/s. A lorry of mass 8000 kg travels at 2.5 m/s. Calculate the momentum of each vehicle and state which would need the larger average force to stop it in the same time.",
                  los=["M1", "F1"], cognitive="multi_step_reasoning",
                  given=[g("m1", 1200, "kg", "car mass"), g("v1", 15, "m/s", "car speed"), g("m2", 8000, "kg", "lorry mass"), g("v2", 2.5, "m/s", "lorry speed")],
                  final="car 18 000 kg m/s; lorry 20 000 kg m/s; the lorry needs the larger force",
                  worked="p(car) = 1200 × 15 = 18 000 kg m/s; p(lorry) = 8000 × 2.5 = 20 000 kg m/s. Same stopping time ⇒ F = Δp/Δt is larger for the lorry.",
                  points=[("Car momentum 18 000 kg m/s", 1), ("Lorry momentum 20 000 kg m/s", 1), ("Lorry: larger change of momentum in same time needs larger force", 1)]),
         genome(qid, "momentum", secondary=["velocity", "force as rate of change of momentum"], prereq=["mass", "velocity", "force"], los=["M1", "F1"], context="road transport",
                reasoning=lin("read_given", "select_relation", "apply_mathematics", "apply_mathematics", "compare", "interpret_result"), math=1),
         num("m2*v2", {"m2": 8000, "v2": 2.5}, 20000, "kg m/s"), judge(), "Adds a second calculation and an interpretation stage (comparison of stopping force).")

    # p2-a3 parameter — try1 copies the parent wording (should be rejected), try2 reworded
    qid = "m-p2-a3-par"
    cand("c06-try1", "p2-a3", "parameter",
         question(qid + "-t1", "Forces", "Hooke's law", "calculation", 2, "A",
                  "A spring with spring constant 40 N/m is extended by 0.19 m. Calculate the force applied to the spring.",
                  los=["F2"], cognitive="application",
                  given=[g("k", 40, "N/m", "spring constant"), g("x", 0.19, "m", "extension")],
                  constraints=[{"text": "the spring obeys Hooke's law (limit of proportionality not exceeded)", "kind": "explicit"}],
                  final="7.6 N", worked="F = kx = 40 × 0.19 = 7.6 N", points=[("F = kx", 1), ("7.6 N", 1)]),
         genome(qid + "-t1", "Hooke's law", secondary=["elastic deformation"], prereq=["force"], los=["F2"], context="spring",
                reasoning=lin("read_given", "select_relation", "apply_mathematics", "derive_result"), explicit=["limit of proportionality not exceeded"], math=1),
         num("k*x", {"k": 40, "x": 0.19}, 7.6, "N"), judge(), "Only the extension changed (first attempt).")
    cand("c06-try2", "p2-a3", "parameter",
         question(qid, "Forces", "Hooke's law", "calculation", 2, "A",
                  "When a student hangs a load on a spring of stiffness 40 N/m, it stretches by 0.19 m without passing its limit of proportionality. What force does the load exert on the spring?",
                  los=["F2"], cognitive="application",
                  given=[g("k", 40, "N/m", "spring constant"), g("x", 0.19, "m", "extension")],
                  constraints=[{"text": "the spring obeys Hooke's law (limit of proportionality not exceeded)", "kind": "explicit"}],
                  final="7.6 N", worked="F = kx = 40 × 0.19 = 7.6 N", points=[("F = kx", 1), ("7.6 N", 1)]),
         genome(qid, "Hooke's law", secondary=["elastic deformation"], prereq=["force"], los=["F2"], context="spring",
                reasoning=lin("read_given", "select_relation", "apply_mathematics", "derive_result"), explicit=["limit of proportionality not exceeded"], math=1),
         num("k*x", {"k": 40, "x": 0.19}, 7.6, "N"), judge(), "Extension changed to 0.19 m; scenario reworded; answer recomputed.")

    # p2-a4 reverse (MC)
    qid = "m-p2-a4-rev"
    cand("c07", "p2-a4", "reverse",
         question(qid, "Waves", "Wave equation", "multiple_choice", 1, "A",
                  "A sound wave of frequency 250 Hz has a wavelength of 1.36 m in air. What is the speed of sound in the air?",
                  los=["W1"], cognitive="application",
                  given=[g("f", 250, "Hz", "frequency"), g("lam", 1.36, "m", "wavelength")],
                  options=[("A", "184 m/s"), ("B", "340 m/s"), ("C", "0.0054 m/s"), ("D", "251 m/s")],
                  answer_key="B", final="340 m/s", points=[("B", 1)]),
         genome(qid, "wave equation", secondary=["sound"], prereq=["frequency"], los=["W1"], context="sound",
                reasoning=lin("read_given", "select_relation", "apply_mathematics"), math=1, answer="choice"),
         num("f*lam", {"f": 250, "lam": 1.36}, 340, "m/s"), judge(), "The former result type (wavelength) is now given and the former given (speed) is the unknown.")

    # p2-a5 context transfer
    qid = "m-p2-a5-ctx"
    cand("c08", "p2-a5", "context_transfer",
         question(qid, "Electricity", "Current and charge", "calculation", 2, "A",
                  "The motor of a kitchen food mixer passes 2700 C of charge during 900 s of use. Calculate the average current in the motor.",
                  los=["C2"], cognitive="application",
                  given=[g("Q", 2700, "C", "charge"), g("t", 900, "s", "time")],
                  final="3.0 A", worked="I = Q/t = 2700/900 = 3.0 A", points=[("I = Q/t", 1), ("3.0 A", 1)]),
         genome(qid, "electric current", secondary=["charge"], prereq=["charge"], los=["C2"], context="kitchen appliances",
                reasoning=lin("read_given", "select_relation", "apply_mathematics", "derive_result"), math=1),
         num("Q/t", {"Q": 2700, "t": 900}, 3.0, "A"), judge(context=False), "Moved from a lamp to a food-mixer motor; same relation and steps.")

    # p3-a2 difficulty up
    qid = "m-p3-a2-diff"
    cand("c09", "p3-a2", "difficulty",
         question(qid, "Energy", "Gravitational potential energy", "calculation", 3, "A",
                  "A climber of mass 55 kg ascends a vertical wall of height 15 m in 50 s. Calculate the climber's gain in gravitational potential energy and the minimum average useful power developed. Take g = 9.8 m/s².",
                  los=["E1", "E2"], cognitive="multi_step_reasoning",
                  given=[g("m", 55, "kg", "mass"), g("h", 15, "m", "height"), g("t", 50, "s", "time"), g("g", 9.8, "m/s^2", "gravitational field strength", role="constant")],
                  final="8085 J (8.1 kJ); 162 W", worked="ΔEp = mgh = 55 × 9.8 × 15 = 8085 J; P = ΔEp/t = 8085/50 = 161.7 ≈ 162 W (minimum, as other energy transfers are ignored).",
                  points=[("ΔEp = mgh = 8085 J", 1), ("P = E/t", 1), ("162 W, identified as a minimum", 1)]),
         genome(qid, "gravitational potential energy", secondary=["power"], prereq=["weight", "power"], los=["E1", "E2"], context="climbing",
                reasoning=lin("read_given", "select_relation", "apply_mathematics", "select_relation", "apply_mathematics", "interpret_result"), math=1),
         num("m*g*h/t", {"m": 55, "g": 9.8, "h": 15, "t": 50}, 161.7, "W"), judge(), "Adds a power stage and an interpretation of why the value is a minimum.")

    # p3-a3 context transfer (projectile → concert stage)
    qid = "m-p3-a3-ctx"
    cand("c10", "p3-a3", "context_transfer",
         question(qid, "Kinematics", "Projectile motion", "calculation", 3, "A",
                  "During an outdoor concert a drumstick rolls horizontally off the edge of a stage riser 1.25 m above the ground. Ignoring air resistance, calculate the time the drumstick takes to reach the ground. Take g = 9.8 m/s².",
                  los=["K3", "K1"], cognitive="multi_step_reasoning",
                  given=[g("h", 1.25, "m", "height of riser"), g("g", 9.8, "m/s^2", "gravitational field strength", role="constant")],
                  constraints=[{"text": "air resistance is negligible", "kind": "explicit"}, {"text": "initial vertical velocity is zero", "kind": "boundary"}],
                  final="0.51 s", worked="Vertical motion from zero vertical velocity: h = ½gt² ⇒ t = √(2h/g) = √(2.5/9.8) = 0.51 s",
                  points=[("Initial vertical velocity zero / horizontal motion irrelevant", 1), ("h = ½gt²", 1), ("0.51 s", 1)]),
         genome(qid, "projectile motion", secondary=["uniformly accelerated motion"], prereq=["acceleration", "vector components"], los=["K3", "K1"], context="music and acoustics (concert stage)",
                reasoning=lin("read_given", "identify_constraint", "construct_model", "select_relation", "apply_mathematics", "derive_result"),
                explicit=["air resistance negligible"], boundary=["initial vertical velocity zero"], math=3),
         num("sqrt(2*h/g)", {"h": 1.25, "g": 9.8}, 0.505, "s"), judge(context=False), "Same projectile model in a concert setting.")

    # p3-a4 representation → table (agent omits judgements: should be REVIEW_REQUIRED)
    qid = "m-p3-a4-rep"
    cand("c11", "p3-a4", "representation",
         question(qid, "Waves", "Wave equation", "calculation", 2, "A",
                  "A student measures a wave on a stretched string. The results are recorded in the table below. Calculate the frequency of the wave.",
                  los=["W1"], cognitive="application",
                  given=[g("v", 15, "m/s", "wave speed"), g("lam", 0.60, "m", "wavelength")],
                  table={"caption": "Measurements", "columns": ["Quantity", "Value"], "rows": [["wave speed", "15 m/s"], ["wavelength", "0.60 m"]]},
                  final="25 Hz", worked="f = v/λ = 15/0.60 = 25 Hz", points=[("f = v/λ", 1), ("25 Hz", 1)]),
         genome(qid, "wave equation", prereq=["frequency", "wavelength"], los=["W1"], context="music and acoustics",
                reasoning=lin("read_representation", "select_relation", "apply_mathematics", "derive_result"), rep=("verbal", "table"), math=1),
         num("v/lam", {"v": 15, "lam": 0.60}, 25, "Hz"), [], "Data moved into a table.")

    # p1-b1 parameter — try1 forgets to update the answer, try2 correct
    def braking(qid_, a_claim, final_, worked_):
        return question(qid_, "Kinematics", "Stopping distance", "mixed", 7, "B",
                        "Travelling along a straight road at 20 m/s, a driver applies the brakes. The car decelerates uniformly and stops after covering 62 m.",
                        los=["K1", "F3"], cognitive="multi_step_reasoning",
                        given=[g("u", 20, "m/s", "initial speed"), g("s", 62, "m", "braking distance")],
                        parts=[("a", "Find the size of the car's deceleration.", 3), ("b", "Find how long the car takes to stop.", 2),
                               ("c", "Explain how an icy road surface would affect the stopping distance.", 2)],
                        constraints=[{"text": "deceleration is uniform", "kind": "explicit"}, {"text": "the car comes to rest (v = 0)", "kind": "boundary"}],
                        final=final_, worked=worked_,
                        points=[("Selects v² = u² − 2as with v = 0", 1, "a"), ("Rearranges for a", 1, "a"), (f"{a_claim} m/s²", 1, "a"),
                                ("t = u/a or equivalent", 1, "b"), ("Correct time", 1, "b"),
                                ("Less friction / grip on ice", 1, "c"), ("Smaller deceleration so longer stopping distance", 1, "c")])

    def braking_genome(qid_):
        return genome(qid_, "uniformly accelerated motion", secondary=["friction", "stopping distance"], prereq=["acceleration", "velocity"], los=["K1", "F3"], context="road transport",
                      reasoning=lin("read_given", "identify_constraint", "select_relation", "apply_mathematics", "derive_result", "select_relation", "derive_result", "justify",
                                    edges=[["s1", "s2"], ["s2", "s3"], ["s3", "s4"], ["s4", "s5"], ["s5", "s6"], ["s6", "s7"], ["s2", "s8"]]),
                      explicit=["deceleration is uniform"], boundary=["final velocity is zero"], math=2, answer="mixed")

    cand("c12-try1", "p1-b1", "parameter", braking("m-p1-b1-par-t1", "4.0", "(a) 4.0 m/s² (b) 5.0 s (c) less friction, so longer distance", "(a) a = 4.0 m/s² (b) t = 5.0 s"),
         braking_genome("m-p1-b1-par-t1"), num("u**2/(2*s)", {"u": 20, "s": 62}, 4.0, "m/s^2"), judge(), "Distance changed to 62 m (answer not recomputed).")
    cand("c12-try2", "p1-b1", "parameter", braking("m-p1-b1-par", "3.2", "(a) 3.2 m/s² (b) 6.2 s (c) less friction on ice, so smaller deceleration and longer distance",
                                                   "(a) a = u²/(2s) = 400/124 = 3.2 m/s² (b) t = u/a = 20/3.23 = 6.2 s (c) Ice reduces friction, so the maximum deceleration is smaller and the car travels further."),
         braking_genome("m-p1-b1-par"), num("u**2/(2*s)", {"u": 20, "s": 62}, 3.226, "m/s^2", domain=[{"var": "result", "min": 0}]), judge(), "Distance changed to 62 m; all answers recomputed; reworded.")

    # p1-b2 surface
    qid = "m-p1-b2-surf"
    cand("c13", "p1-b2", "surface",
         question(qid, "Energy", "Energy conservation", "mixed", 7, "B",
                  "A 0.50 kg ball is released from rest 3.2 m above level ground. Drag is negligible; use g = 9.8 m/s².",
                  los=["E1"], cognitive="multi_step_reasoning",
                  given=[g("m", 0.50, "kg", "mass"), g("h", 3.2, "m", "height"), g("g", 9.8, "m/s^2", "gravitational field strength", role="constant")],
                  parts=[("a", "Determine the decrease in gravitational potential energy during the fall.", 2),
                         ("b", "Find the speed of the ball at the instant before impact.", 3),
                         ("c", "State and explain the effect on this impact speed if drag were significant.", 2)],
                  constraints=[{"text": "air resistance is negligible", "kind": "explicit"}, {"text": "released from rest", "kind": "boundary"}],
                  final="(a) 15.7 J (b) 7.9 m/s (c) lower: energy is transferred to the surroundings by drag",
                  worked="(a) mgh = 0.50 × 9.8 × 3.2 = 15.68 J. (b) v = √(2gh) = 7.9 m/s. (c) Work done against drag ⇒ less kinetic energy ⇒ lower speed.",
                  points=[("ΔEp = mgh", 1, "a"), ("15.7 J", 1, "a"), ("Ek gained = Ep lost", 1, "b"), ("v = √(2gh)", 1, "b"), ("7.9 m/s", 1, "b"),
                          ("Work done against drag", 1, "c"), ("Less kinetic energy so lower speed", 1, "c")]),
         genome(qid, "conservation of energy", secondary=["gravitational potential energy", "kinetic energy"], prereq=["energy stores", "work"], los=["E1"], context="dropped ball",
                reasoning=lin("read_given", "select_relation", "apply_mathematics", "construct_model", "apply_mathematics", "derive_result", "interpret_result"),
                explicit=["air resistance is negligible"], boundary=["released from rest"], math=2, answer="mixed"),
         num("m*g*h", {"m": 0.50, "g": 9.8, "h": 3.2}, 15.68, "J"), judge(), "Concise technical restatement with identical data and method.")

    # p1-b3 reverse — try1 has multiple valid answers and no accept rule, try2 unique
    cand("c14-try1", "p1-b3", "reverse",
         question("m-p1-b3-rev-t1", "Electricity", "Series circuits", "calculation", 6, "B",
                  "A 4.0 Ω resistor and a second resistor R are connected in series with a 12 V battery of negligible internal resistance. The current must be less than 1.5 A.",
                  los=["C1"], cognitive="multi_step_reasoning",
                  given=[g("V", 12, "V", "battery p.d."), g("R1", 4.0, "ohm", "first resistance"), g("I", 1.5, "A", "maximum current")],
                  parts=[("a", "Suggest a suitable value for R.", 3), ("b", "Calculate the potential difference across R for your value.", 3)],
                  constraints=[{"text": "battery has negligible internal resistance", "kind": "explicit"}],
                  final="(a) any R greater than 4.0 Ω, e.g. 6.0 Ω (b) 7.2 V for 6.0 Ω",
                  points=[("Total resistance > 8.0 Ω", 1, "a"), ("R > 4.0 Ω", 1, "a"), ("Suitable value", 1, "a"), ("I = V/R_total", 1, "b"), ("V = IR", 1, "b"), ("Consistent value", 1, "b")]),
         genome("m-p1-b3-rev-t1", "series circuit", secondary=["Ohm's law"], prereq=["resistance", "current"], los=["C1"], context="circuit",
                reasoning=lin("read_given", "construct_model", "apply_mathematics", "select_relation", "apply_mathematics", "derive_result"), explicit=["negligible internal resistance"], math=1),
         num("V/I - R1", {"V": 12, "I": 1.5, "R1": 4.0}, 4.0, "ohm", answer_uniqueness="multiple"), judge(), "Inverted: find R from a current condition (first attempt).")
    qid = "m-p1-b3-rev"
    cand("c14-try2", "p1-b3", "reverse",
         question(qid, "Electricity", "Series circuits", "calculation", 6, "B",
                  "A 4.0 Ω resistor and an unknown resistor R are connected in series with a 12 V battery of negligible internal resistance. The current in the circuit is 1.5 A.",
                  los=["C1"], cognitive="multi_step_reasoning",
                  given=[g("V", 12, "V", "battery p.d."), g("R1", 4.0, "ohm", "known resistance"), g("I", 1.5, "A", "current")],
                  parts=[("a", "Calculate the total resistance of the circuit.", 2), ("b", "Determine the resistance R.", 2), ("c", "Calculate the potential difference across R.", 2)],
                  constraints=[{"text": "battery has negligible internal resistance", "kind": "explicit"}],
                  final="(a) 8.0 Ω (b) 4.0 Ω (c) 6.0 V",
                  worked="(a) R_total = V/I = 12/1.5 = 8.0 Ω. (b) R = 8.0 − 4.0 = 4.0 Ω. (c) V_R = IR = 1.5 × 4.0 = 6.0 V.",
                  points=[("R_total = V/I", 1, "a"), ("8.0 Ω", 1, "a"), ("R = R_total − 4.0", 1, "b"), ("4.0 Ω", 1, "b"), ("V = IR", 1, "c"), ("6.0 V", 1, "c")]),
         genome(qid, "series circuit", secondary=["Ohm's law"], prereq=["resistance", "current"], los=["C1"], context="circuit",
                reasoning=lin("read_given", "select_relation", "apply_mathematics", "construct_model", "apply_mathematics", "derive_result"), explicit=["negligible internal resistance"], math=1),
         num("V/I - R1", {"V": 12, "I": 1.5, "R1": 4.0}, 4.0, "ohm", domain=[{"var": "result", "min": 0, "exclusive": True}]), judge(),
         "Inverted: the current is given and the second resistance is the unknown; the answer is unique.")

    # p2-b1 reasoning path: opposite directions, sign convention, energy evaluation
    qid = "m-p2-b1-path"
    cand("c15", "p2-b1", "reasoning_path",
         question(qid, "Momentum", "Collisions", "mixed", 8, "B",
                  "Trolley X (mass 2.0 kg) moves to the right at 3.0 m/s. Trolley Y (mass 1.0 kg) moves to the left at 1.5 m/s. They collide head-on and stick together.",
                  los=["M1", "E1"], cognitive="evaluation",
                  given=[g("m1", 2.0, "kg", "mass of X"), g("u1", 3.0, "m/s", "speed of X (to the right)"), g("m2", 1.0, "kg", "mass of Y"), g("u2", 1.5, "m/s", "speed of Y (to the left)")],
                  parts=[("a", "Taking right as positive, calculate the total momentum before the collision.", 2),
                         ("b", "Determine the velocity of the trolleys after the collision.", 3),
                         ("c", "Evaluate whether kinetic energy is conserved in the collision.", 3)],
                  constraints=[{"text": "momentum to the right is positive", "kind": "explicit"}, {"text": "trolleys stick together", "kind": "explicit"}],
                  final="(a) 4.5 kg m/s (b) 1.5 m/s to the right (c) not conserved: 10.1 J before, 3.4 J after",
                  worked="(a) p = 2.0 × 3.0 + 1.0 × (−1.5) = 4.5 kg m/s. (b) v = 4.5/3.0 = 1.5 m/s to the right. (c) Ek before = 9.0 + 1.125 = 10.1 J; after = ½ × 3.0 × 1.5² = 3.4 J; kinetic energy is not conserved (inelastic).",
                  points=[("Sign convention applied to Y", 1, "a"), ("4.5 kg m/s", 1, "a"), ("Momentum conserved", 1, "b"), ("v = p/(m1 + m2)", 1, "b"), ("1.5 m/s to the right", 1, "b"),
                          ("Ek before 10.1 J", 1, "c"), ("Ek after 3.4 J", 1, "c"), ("Conclusion: not conserved", 1, "c")]),
         genome(qid, "conservation of momentum", secondary=["kinetic energy", "inelastic collision", "sign convention"], prereq=["momentum", "vectors"], los=["M1", "E1"], context="laboratory trolley",
                reasoning=lin("read_given", "identify_constraint", "construct_model", "apply_mathematics", "derive_result", "apply_mathematics", "compare", "evaluate"),
                explicit=["momentum to the right is positive", "trolleys stick together"], math=2, answer="mixed"),
         num("(m1*u1 - m2*u2)/(m1 + m2)", {"m1": 2.0, "u1": 3.0, "m2": 1.0, "u2": 1.5}, 1.5, "m/s"), judge(),
         "Head-on collision requires a sign convention and an evaluation of energy conservation instead of a direct energy-loss calculation.")

    # p2-b3 constraint add (fuse rating)
    qid = "m-p2-b3-con"
    cand("c16", "p2-b3", "constraint",
         question(qid, "Electricity", "Electrical power", "mixed", 6, "B",
                  "A kettle connected to a 230 V supply draws a current of 8.0 A. The kettle and a toaster drawing 6.0 A are plugged into an adaptor protected by a 13 A fuse.",
                  los=["C2", "E2"], cognitive="application",
                  given=[g("V", 230, "V", "supply voltage"), g("I", 8.0, "A", "kettle current"), g("t", 150, "s", "heating time"), g("I2", 6.0, "A", "toaster current", role="data")],
                  parts=[("a", "Calculate the power of the kettle.", 2), ("b", "Calculate the energy transferred by the kettle in 150 s.", 2),
                         ("c", "Determine whether the fuse melts when both appliances are switched on together.", 2)],
                  constraints=[{"text": "the fuse melts if the total current exceeds 13 A", "kind": "explicit"}],
                  final="(a) 1840 W (b) 2.8 × 10^5 J (c) yes: total current 14 A exceeds 13 A",
                  worked="(a) P = VI = 230 × 8.0 = 1840 W. (b) E = Pt = 1840 × 150 = 276 000 J ≈ 2.8 × 10⁵ J. (c) I_total = 8.0 + 6.0 = 14 A > 13 A, so the fuse melts.",
                  points=[("P = VI", 1, "a"), ("1840 W", 1, "a"), ("E = Pt", 1, "b"), ("2.8 × 10⁵ J", 1, "b"), ("Total current 14 A", 1, "c"), ("Exceeds 13 A so fuse melts", 1, "c")]),
         genome(qid, "electrical power", secondary=["energy transfer", "fuse rating"], prereq=["current", "potential difference"], los=["C2", "E2"], context="household appliances",
                reasoning=lin("read_given", "select_relation", "apply_mathematics", "select_relation", "apply_mathematics", "apply_mathematics", "compare",
                              edges=[["s1", "s2"], ["s2", "s3"], ["s3", "s4"], ["s4", "s5"], ["s1", "s6"], ["s6", "s7"]]),
                explicit=["total current must not exceed 13 A fuse rating"], math=1, answer="mixed"),
         num("V*I", {"V": 230, "I": 8.0}, 1840, "W"), judge(), "Adds a fuse-rating constraint that must be checked against the combined current.")

    # p3-b1 difficulty up (adds cable-rating stage; interacting constraint + prerequisite)
    qid = "m-p3-b1-diff"
    cand("c17", "p3-b1", "difficulty",
         question(qid, "Forces", "Newton's second law", "mixed", 7, "B",
                  "A lift of total mass 900 kg is supported by a cable with a maximum safe tension of 11 000 N. Take g = 9.8 m/s².",
                  los=["F1", "F3"], cognitive="multi_step_reasoning",
                  given=[g("m", 900, "kg", "mass of lift"), g("Tmax", 11000, "N", "maximum safe tension"), g("a", 1.5, "m/s^2", "planned upward acceleration"), g("g", 9.8, "m/s^2", "gravitational field strength", role="constant")],
                  parts=[("a", "Calculate the tension in the cable when the lift accelerates upwards at 1.5 m/s².", 3),
                         ("b", "Calculate the maximum upward acceleration that keeps the tension within the safe limit.", 3),
                         ("c", "State whether the planned acceleration of 1.5 m/s² is safe.", 1)],
                  constraints=[{"text": "tension must not exceed 11 000 N", "kind": "explicit", "var": "Tmax", "op": "<=", "value": 11000},
                               {"text": "acceleration is upward and uniform", "kind": "explicit"}],
                  final="(a) 1.0 × 10^4 N (10 170 N) (b) 2.4 m/s² (c) safe: 1.5 < 2.4 m/s²",
                  worked="(a) T = m(g + a) = 900 × 11.3 = 10 170 N. (b) a_max = Tmax/m − g = 11 000/900 − 9.8 = 2.42 m/s². (c) 1.5 m/s² < 2.4 m/s², so safe.",
                  points=[("T − mg = ma", 1, "a"), ("T = m(g + a)", 1, "a"), ("10 170 N", 1, "a"), ("Tmax − mg = m a_max", 1, "b"), ("Rearranges", 1, "b"), ("2.4 m/s²", 1, "b"), ("Safe, with comparison", 1, "c")]),
         genome(qid, "Newton's second law", secondary=["weight", "safety limit"], prereq=["force", "acceleration", "rearranging equations"], los=["F1", "F3"], context="building lift",
                reasoning=lin("read_given", "select_relation", "apply_mathematics", "construct_model", "identify_constraint", "apply_mathematics", "derive_result", "compare"),
                explicit=["acceleration upward and uniform", "tension must not exceed 11 000 N"], boundary=["tension at the safe limit"], math=2, answer="mixed"),
         num("Tmax/m - g", {"Tmax": 11000, "m": 900, "g": 9.8}, 2.42, "m/s^2", domain=[{"var": "result", "min": 0}]), judge(),
         "Adds a cable-rating limit: an extra constraint, a boundary condition and a rearrangement stage.")

    # p3-b2 representation verbal → graph
    qid = "m-p3-b2-rep"
    cand("c18", "p3-b2", "representation",
         question(qid, "Energy", "Efficiency", "calculation", 7, "B",
                  "A motor lifts a 20 kg load through a vertical height of 5.0 m in 10 s. The graph shows the total energy supplied to the motor against time during the lift. Take g = 9.8 m/s².",
                  los=["E1", "E2", "K2"], cognitive="multi_step_reasoning",
                  given=[g("m", 20, "kg", "mass of load"), g("h", 5.0, "m", "height"), g("Ein", 2000, "J", "energy supplied in 10 s (read from graph)"), g("g", 9.8, "m/s^2", "gravitational field strength", role="constant"), g("t", 10, "s", "time", role="data")],
                  diagram="Graph of energy supplied E / J (vertical axis, 0 to 2500) against time t / s (horizontal axis, 0 to 12): a straight line through the origin reaching 2000 J at 10 s.",
                  parts=[("a", "Calculate the useful energy transferred to the load.", 2), ("b", "Use the graph to determine the input power to the motor.", 2), ("c", "Calculate the efficiency of the motor.", 3)],
                  final="(a) 980 J (b) 200 W (c) 0.49 (49 %)",
                  worked="(a) mgh = 20 × 9.8 × 5.0 = 980 J. (b) gradient = 2000/10 = 200 W. (c) efficiency = 980/2000 = 0.49.",
                  points=[("mgh", 1, "a"), ("980 J", 1, "a"), ("Power = gradient", 1, "b"), ("200 W", 1, "b"), ("efficiency = useful/total", 1, "c"), ("Uses 980 and 2000", 1, "c"), ("0.49 or 49 %", 1, "c")]),
         genome(qid, "efficiency", secondary=["gravitational potential energy", "power", "gradient"], prereq=["energy", "power"], los=["E1", "E2", "K2"], context="construction and engineering",
                reasoning=lin("read_given", "select_relation", "apply_mathematics", "read_representation", "apply_mathematics", "construct_model", "derive_result",
                              edges=[["s1", "s2"], ["s2", "s3"], ["s1", "s4"], ["s4", "s5"], ["s3", "s6"], ["s5", "s6"], ["s6", "s7"]]),
                rep=("verbal", "graph"), math=2),
         num("m*g*h/Ein", {"m": 20, "g": 9.8, "h": 5.0, "Ein": 2000}, 0.49, "1", domain=[{"var": "result", "min": 0, "max": 1}]), judge(),
         "Input energy is now read from an energy–time graph; input power is its gradient.")
    return C


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 1
    ws = Path(argv[1])
    plan = json.loads((ws / "mutation_plan.json").read_text(encoding="utf-8"))
    index = {(s["parent_id"], s["operator"]): s["spec_id"] for s in plan["specs"]}

    def spec_for(parent, op):
        if (parent, op) not in index:
            raise SystemExit(f"demo plan has no spec for {parent}/{op}; the plan options changed")
        return index[(parent, op)]

    candidates = build(spec_for)
    (ws / "candidates.json").write_text(json.dumps({"candidates": candidates}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {len(candidates)} candidates")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
