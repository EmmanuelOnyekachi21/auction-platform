/** Temporary placeholder for admin sections not yet built. */
export default function AdminPlaceholderPage({ title = 'Coming Soon' }) {
  return (
    <div style={{ padding: '2rem' }}>
      <div className="card text-center p-5" style={{ borderRadius: 'var(--radius-xl)', borderStyle: 'dashed', background: 'transparent' }}>
        <h3 style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>{title}</h3>
        <p style={{ color: 'var(--text-muted)', margin: 0 }}>This section is under construction.</p>
      </div>
    </div>
  );
}
