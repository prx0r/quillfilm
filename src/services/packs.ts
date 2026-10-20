// Video-idea packs: one film = one manuscript + its evidence bank, fetched
// from the same origin (/packs/<slug>/) and loaded into the editor + Cite
// library in one click. No import dialogs, no digest pipeline — chat-attach
// works on the raw verbatim text, which is what the compiler law needs.

export interface PackManuscript {
  file: string;
  title: string;
}

export interface PackDef {
  slug: string;
  title: string;
  blurb: string;
  manuscripts: PackManuscript[];
  /** Source filenames under /packs/<slug>/sources/. First entry doubles as the manuscript. */
  sources: string[];
}

export interface PackManifest {
  packs: PackDef[];
}

export async function fetchPackManifest(): Promise<PackManifest> {
  const res = await fetch('/packs/packs.json');
  if (!res.ok) throw new Error(`packs manifest: HTTP ${res.status}`);
  const data = (await res.json()) as PackManifest;
  if (!Array.isArray(data.packs)) throw new Error('packs manifest malformed');
  return data;
}

export async function fetchPackFile(slug: string, kind: 'manuscripts' | 'sources', file: string): Promise<string> {
  const res = await fetch(`/packs/${slug}/${kind}/${encodeURIComponent(file)}`);
  if (!res.ok) throw new Error(`${file}: HTTP ${res.status}`);
  return res.text();
}
