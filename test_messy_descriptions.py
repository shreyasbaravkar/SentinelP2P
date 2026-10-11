import numpy as np
from sentence_transformers import SentenceTransformer

services = [
    "printing and packaging materials", "catering services", "software licenses",
    "logistics and courier services", "IT hardware equipment", "cleaning services",
    "office supplies",
]

cases = [
    ("Corporate brochure printing and carton boxes", "printing and packaging materials"),
    ("Packaging material for Q3 dispatch", "printing and packaging materials"),
    ("Bulk printing of letterheads and visiting cards", "printing and packaging materials"),
    ("Bubble wrap and corrugated sheets", "printing and packaging materials"),
    ("Lunch and snacks for annual day event", "catering services"),
    ("Tea, coffee and refreshments for client meeting", "catering services"),
    ("Dinner buffet for staff celebration", "catering services"),
    ("Catering for board meeting 12 Oct", "catering services"),
    ("Annual Microsoft 365 subscription renewal", "software licenses"),
    ("Adobe Creative Cloud licences (10 seats)", "software licenses"),
    ("Antivirus subscription renewal", "software licenses"),
    ("ERP software license fee - yearly", "software licenses"),
    ("Courier charges for document dispatch", "logistics and courier services"),
    ("Freight charges Mumbai to Pune", "logistics and courier services"),
    ("Shipment of goods to regional warehouse", "logistics and courier services"),
    ("Last-mile delivery service for October", "logistics and courier services"),
    ("Laptops for new joiners", "IT hardware equipment"),
    ("Purchase of 20 monitors and keyboards", "IT hardware equipment"),
    ("Network switches and server rack", "IT hardware equipment"),
    ("Dell desktops and UPS", "IT hardware equipment"),
    ("Monthly office housekeeping service", "cleaning services"),
    ("Deep cleaning of 3rd floor", "cleaning services"),
    ("Janitorial services and washroom supplies", "cleaning services"),
    ("Sanitisation of premises", "cleaning services"),
    ("A4 paper reams and pens", "office supplies"),
    ("Stationery for finance department", "office supplies"),
    ("Office chairs and desks", "office supplies"),
    ("Whiteboards, markers and files", "office supplies"),
]

model = SentenceTransformer("all-MiniLM-L6-v2")
svec = model.encode(services, normalize_embeddings=True)
dvec = model.encode([c[0] for c in cases], normalize_embeddings=True)
sims = dvec @ svec.T

THRESHOLD = 0.50
top1_correct = 0
below_cutoff = 0
true_scores = []

print(f"{'description':50s} {'expected':32s} {'predicted':32s} true_score")
for i, (desc, expected) in enumerate(cases):
    pred = services[int(np.argmax(sims[i]))]
    true_score = float(sims[i][services.index(expected)])
    true_scores.append(true_score)
    top1_correct += pred == expected
    below_cutoff += true_score < THRESHOLD
    mark = "" if pred == expected else "  <-- WRONG"
    print(f"{desc[:50]:50s} {expected:32s} {pred:32s} {true_score:.2f}{mark}")

print()
print(f"Right service ranked first: {top1_correct}/{len(cases)}")
print(f"Correct matches scoring below the {THRESHOLD} cutoff (would be false mismatches): {below_cutoff}/{len(cases)}")
print(f"Average score for the correct service: {np.mean(true_scores):.2f}")

# --- Compare decision rules on matches AND mismatches ---
exp_idx = [services.index(e) for _, e in cases]
ranks = np.argsort(-sims, axis=1).argsort(axis=1) + 1  # rank 1 = best

rules = {
    "fixed cutoff 0.50":       lambda s, r, best: s >= 0.50,
    "vendor service is top-1": lambda s, r, best: r <= 1,
    "vendor service in top-2": lambda s, r, best: r <= 2,
    "within 0.10 of best":     lambda s, r, best: s >= best - 0.10,
    "top-1 OR score >= 0.50":  lambda s, r, best: r <= 1 or s >= 0.50,
}

print()
print(f"{'rule':26s} {'legit wrongly flagged':>24s} {'mismatches caught':>22s}")
for name, ok in rules.items():
    false_flags = total_match = caught = total_mis = 0
    for i, e in enumerate(exp_idx):
        best = sims[i].max()
        for j in range(len(services)):
            passes = ok(sims[i][j], ranks[i][j], best)
            if j == e:
                total_match += 1
                false_flags += (not passes)
            else:
                total_mis += 1
                caught += (not passes)
    print(f"{name:26s} {false_flags:3d}/{total_match} ({false_flags/total_match:4.0%})"
          f"{caught:14d}/{total_mis} ({caught/total_mis:4.0%})")