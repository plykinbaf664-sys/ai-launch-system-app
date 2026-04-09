import HypothesisCard from "@/components/HypothesisCard";

export default function ResearchPage() {
  return (
    <main style={{ padding: "32px", maxWidth: "1400px", margin: "0 auto" }}>
      <h1 style={{ marginBottom: "8px" }}>Research Hub</h1>
      <p style={{ marginTop: 0, marginBottom: "24px", color: "#4b5563", lineHeight: 1.5 }}>
        Здесь можно быстро собрать живые отзывы из открытых источников под конкретную нишу и
        позиционирование эксперта.
      </p>

      <HypothesisCard />
    </main>
  );
}
