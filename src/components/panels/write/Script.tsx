import { useCallback, useMemo, useState } from 'react';
import { useDocumentStore } from '../../../stores/useDocumentStore';

interface ScriptSection {
  title: string;
  text: string;
  words: number;
  estSec: number;
}

/** Split editor HTML into sections by h2/h3, clean for TTS, count words. */
function extractSections(html: string): ScriptSection[] {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const sections: ScriptSection[] = [];
  let current: { title: string; parts: string[] } | null = null;
  const flush = () => {
    if (!current) return;
    const raw = current.parts.join('\n');
    // TTS cleanup: strip stage directions, READ/OWNER markers, markdown artefacts
    const text = raw
      .replace(/^>?\s*DIR:.*$/gm, '')
      .replace(/\[READ[^\]]*\]:?\s*/g, '')
      .replace(/\[OWNER VERBATIM\]\s*/g, '')
      .replace(/\[DRAFT[^\]]*\]/g, '')
      .replace(/\*\*?/g, '')
      .replace(/^\s*#{1,6}\s+/gm, '')
      .replace(/\[EOF[^\]]*\]/g, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
    const words = text.split(/\s+/).filter(Boolean).length;
    if (words > 3) {
      sections.push({ title: current.title, text, words, estSec: Math.round(words / 2.5) });
    }
    current = null;
  };
  for (const el of doc.body.children) {
    const tag = el.tagName.toLowerCase();
    if (tag === 'h1' || tag === 'h2' || tag === 'h3') {
      flush();
      current = { title: el.textContent || 'Untitled', parts: [] };
    } else if (current) {
      current.parts.push(el.textContent || '');
    }
  }
  flush();
  return sections;
}

const mmss = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

/** Script view: the final TTS wording per section, render→play via Fish.
 * Strips stage directions and citation markers so only spoken words remain.
 * Renders are cached by the bridge (sha of text+voice) — re-renders are instant. */
export function Script() {
  const content = useDocumentStore(s => s.content);
  const sections = useMemo(() => {
    try { return extractSections(content); } catch { return []; }
  }, [content]);
  const [playing, setPlaying] = useState<string | null>(null);
  const [rendering, setRendering] = useState<string | null>(null);
  const [audio, setAudio] = useState<HTMLAudioElement | null>(null);
  const [voice, setVoice] = useState(''); // '' = engine default voice
  const [engine, setEngine] = useState<'phonon' | 'fish'>('phonon'); // local by default

  const totalWords = sections.reduce((s, x) => s + x.words, 0);
  const totalSec = sections.reduce((s, x) => s + x.estSec, 0);

  const render = useCallback(async (sec: ScriptSection) => {
    setRendering(sec.title);
    try {
      const res = await fetch('/api/tts/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: sec.text, label: sec.title, voice, engine }),
      });
      if (!res.ok) {
        const e = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
        alert(`TTS failed: ${e.error || res.status}`);
        return;
      }
      const { id, ext } = await res.json();
      const a = new Audio(`/api/tts/${id}.${ext || 'mp3'}`);
      setAudio(a);
      setPlaying(sec.title);
      a.onended = () => setPlaying(null);
      await a.play().catch(() => { /* blocked autoplay: user clicks again */ });
    } catch (e) {
      alert(`TTS failed: ${e instanceof Error ? e.message : e}`);
    } finally {
      setRendering(null);
    }
  }, [voice, engine]);

  const stop = () => { audio?.pause(); setPlaying(null); };

  if (!sections.length) {
    return <p className="text-[13px]" style={{ color: 'var(--text-muted)' }}>No sections found. Load a pack manuscript (File → Video packs…) and sections will appear here.</p>;
  }

  return (
    <div>
      <div className="text-[12px] mb-2" style={{ color: 'var(--text-muted)' }}>
        {sections.length} sections · {totalWords.toLocaleString()} spoken words · ~{mmss(totalSec)} est
        {' · '}
        <label style={{ color: 'var(--text-muted)' }}>
          voice{' '}
          <select value={engine} onChange={e => setEngine(e.target.value as 'phonon' | 'fish')} data-testid="control-script-engine"
            className="text-[11px] px-1 py-0.5 rounded border mr-2" style={{ background: 'var(--surface-1, #111116)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}>
            <option value="phonon">phonon · local, instant</option>
            <option value="fish">fish · cloud voices</option>
          </select>
          <select value={voice} onChange={e => setVoice(e.target.value)} data-testid="control-script-voice"
            className="text-[11px] px-1 py-0.5 rounded border" style={{ background: 'var(--surface-1, #111116)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}>
            <option value="">fish default</option>
            <option value="fb015415ebf141999fc882baa0e0834c">narrator (louis)</option>
            <option value="dbeb1d68566245e2b857617b830e8031">skeptic (ari)</option>
            <option value="9c36c951cee84457a5cc9f94387e9a42">wonderer (casey)</option>
          </select>
        </label>
        {playing && <button onClick={stop} data-testid="control-script-stop" className="ml-2 text-[11px] px-2 py-0.5 rounded border" style={{ borderColor: '#E8102E', color: '#E8102E' }}>■ stop</button>}
      </div>
      <div className="space-y-2 max-h-96 overflow-auto">
        {sections.map(sec => (
          <div key={sec.title} className="border rounded-lg p-3" style={{ borderColor: 'var(--border)', background: 'var(--surface-1, #111116)' }}>
            <div className="flex items-center justify-between gap-2 mb-1">
              <span className="text-[13px] font-semibold truncate" style={{ color: 'var(--text-primary)' }}>{sec.title}</span>
              <span className="text-[11px] shrink-0" style={{ color: 'var(--text-muted)' }}>
                {sec.words}w · ~{mmss(sec.estSec)}
                <button
                  data-testid="control-script-render"
                  onClick={() => playing === sec.title ? stop() : void render(sec)}
                  disabled={rendering !== null}
                  className="ml-2 px-2 py-0.5 rounded border text-[11px]"
                  style={{ borderColor: playing === sec.title ? '#E8102E' : 'var(--border)', color: playing === sec.title ? '#E8102E' : '#F5C76B' }}
                >
                  {rendering === sec.title ? '…' : playing === sec.title ? '■ stop' : '▶ render'}
                </button>
              </span>
            </div>
            <p className="text-[12px] leading-relaxed" style={{ color: 'var(--text-muted)' }}>
              {sec.text.slice(0, 220)}{sec.text.length > 220 ? '…' : ''}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
