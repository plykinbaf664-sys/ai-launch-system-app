import HypothesisCard from "@/components/HypothesisCard";

export default function ResearchPage() {
  return (
    <main style={{ padding: "32px", maxWidth: "1400px", margin: "0 auto" }}>
      <h1
        style={{
          marginBottom: "8px",
          fontFamily: 'Georgia, "Times New Roman", serif',
          fontWeight: 800,
          letterSpacing: "0.04em",
        }}
      >
        Research Hub
      </h1>
      <p style={{ marginTop: 0, marginBottom: "24px", color: "#4b5563", lineHeight: 1.5 }}>
        {"\u0417\u0434\u0435\u0441\u044c \u043c\u043e\u0436\u043d\u043e \u0431\u044b\u0441\u0442\u0440\u043e \u0441\u043e\u0431\u0440\u0430\u0442\u044c \u0436\u0438\u0432\u044b\u0435 \u043e\u0442\u0437\u044b\u0432\u044b \u0438\u0437 \u043e\u0442\u043a\u0440\u044b\u0442\u044b\u0445 \u0438\u0441\u0442\u043e\u0447\u043d\u0438\u043a\u043e\u0432 \u043f\u043e\u0434 \u043a\u043e\u043d\u043a\u0440\u0435\u0442\u043d\u0443\u044e \u043d\u0438\u0448\u0443 \u0438 \u043f\u043e\u0437\u0438\u0446\u0438\u043e\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u044d\u043a\u0441\u043f\u0435\u0440\u0442\u0430."}
      </p>

      <HypothesisCard />
    </main>
  );
}
