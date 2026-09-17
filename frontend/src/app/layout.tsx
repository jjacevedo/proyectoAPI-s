import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'proyectoAPI-s',
  description: 'Sistema Multi-LLM de Deliberación y Síntesis',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
