# Communicating results and uncertainty

## Always report

- Inputs used, and what could not be read.
- Counts from the engine output (never estimate them): questions extracted, genomes complete, specs planned, candidates generated, PASS / REVIEW_REQUIRED / FAIL, questions in the final exam.
- The blueprint's `evidence_level` and its notes.
- Deviations from the request (marks, sections, topics, difficulty) from `reports/exam_vs_dna.md` and `reports/analysis_report.md`.
- Which checks were model-assisted.

## Wording to use

- "Structurally similar to the supplied papers" — not "equivalent", "same difficulty" or "predicts".
- "Heuristic difficulty band" — not "difficulty level".
- "Recomputed by the engine" for numeric answers that passed `recompute`; "my own worked solution" for answers you wrote without a mark scheme.
- "Best under the stated objective" only if the solver says `exhaustive: true`.

## Do not

- Quote percentages that the engine did not compute.
- Call REVIEW_REQUIRED questions verified.
- Present the exam as official or affiliated with any exam board.

## Incomplete input messages

- One paper: "I only had one paper, so this blueprint is a single example rather than a pattern — the structure may not be typical."
- Notes only: "There is no past exam to learn the format from; I used a simple single-section format. Tell me the sections and marks you want if you have them."
- No mark scheme: "The answers and marking points are my own and have not been checked against an official scheme."

## Turkish (Türkçe)

Kullanıcı Türkçe yazıyorsa Türkçe yanıt verin. Örnek ifadeler:

- "Elimde yalnızca bir sınav olduğu için çıkarılan yapı düşük güvenilirliktedir."
- "Sayısal cevaplar motor tarafından yeniden hesaplandı ve doğrulandı."
- "Bu sorular KONTROL GEREKLİ olarak işaretlendi; öğretmen onayı olmadan doğrulanmış sayılmaz."
- "Bu bir alıştırma sınavıdır; resmî bir sınav değildir ve gerçek sınav sorularını tahmin etmez."

Sınav başlıkları için yapılandırmada `"language": "tr"` kullanın.
