type Props = {
  prompt: string;
  setPrompt: (value: string) => void;
  onSubmit: () => void;
  loading: boolean;
};

export function ChatForm({ prompt, setPrompt, onSubmit, loading }: Props) {
  return (
    <section className="card">
      <textarea
        value={prompt}
        onChange={(event) => setPrompt(event.target.value)}
        placeholder="Escribe una tarea para los modelos..."
        maxLength={12000}
      />
      <button onClick={onSubmit} disabled={loading || !prompt.trim()}>
        {loading ? 'Consultando modelos...' : 'Resolver'}
      </button>
    </section>
  );
}
