export function FinalAnswer({ answer }: { answer: string }) {
  return (
    <section className="card">
      <h2>Respuesta final</h2>
      <div className="response">{answer}</div>
    </section>
  );
}
