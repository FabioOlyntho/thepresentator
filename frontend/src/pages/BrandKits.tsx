import { useState, useEffect, type CSSProperties } from 'react';
import { listBrands, createBrand, updateBrand, deleteBrand } from '../api';
import type { BrandKit, BrandColors, BrandFonts } from '../types';
import BrandKitCard from '../components/BrandKitCard';
import BrandKitForm from '../components/BrandKitForm';

type FormData = {
  name: string;
  colors: BrandColors;
  fonts: BrandFonts;
  logo_position: string;
};

export default function BrandKits() {
  const [brands, setBrands] = useState<BrandKit[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<BrandKit | null>(null);
  const [saving, setSaving] = useState(false);

  function fetchBrands() {
    setLoading(true);
    listBrands()
      .then(setBrands)
      .catch(() => {})
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    fetchBrands();
  }, []);

  async function handleCreate(data: FormData) {
    setSaving(true);
    try {
      await createBrand({
        name: data.name,
        colors: data.colors,
        fonts: data.fonts,
        logo_position: data.logo_position,
      });
      setShowForm(false);
      fetchBrands();
    } catch {
      // error handling
    } finally {
      setSaving(false);
    }
  }

  async function handleUpdate(data: FormData) {
    if (!editing) return;
    setSaving(true);
    try {
      await updateBrand(editing.id, {
        name: data.name,
        colors: data.colors,
        fonts: data.fonts,
        logo_position: data.logo_position,
      });
      setEditing(null);
      fetchBrands();
    } catch {
      // error handling
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(brand: BrandKit) {
    if (brand.is_default) return;
    if (!window.confirm(`Delete brand kit "${brand.name}"?`)) return;
    try {
      await deleteBrand(brand.id);
      fetchBrands();
    } catch {
      // error handling
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Brand Kits</h1>
          <p style={styles.subtitle}>
            Custom branding presets for your presentations
          </p>
        </div>
        {!showForm && !editing && (
          <button onClick={() => setShowForm(true)} style={styles.addBtn}>
            + New Brand Kit
          </button>
        )}
      </div>

      {/* Create Form */}
      {showForm && (
        <div style={styles.formCard}>
          <h3 style={styles.formTitle}>New Brand Kit</h3>
          <BrandKitForm
            onSubmit={handleCreate}
            onCancel={() => setShowForm(false)}
            loading={saving}
          />
        </div>
      )}

      {/* Edit Form */}
      {editing && (
        <div style={styles.formCard}>
          <h3 style={styles.formTitle}>Edit: {editing.name}</h3>
          <BrandKitForm
            initial={{
              name: editing.name,
              colors: editing.colors,
              fonts: editing.fonts,
              logo_position: editing.logo_position,
            }}
            onSubmit={handleUpdate}
            onCancel={() => setEditing(null)}
            loading={saving}
          />
        </div>
      )}

      {/* Brand Grid */}
      {loading ? (
        <div style={styles.loading}>Loading...</div>
      ) : (
        <div style={styles.grid}>
          {brands.map((brand) => (
            <div key={brand.id} style={styles.cardWrapper}>
              <BrandKitCard brand={brand} />
              <div style={styles.cardActions}>
                <button
                  onClick={() => setEditing(brand)}
                  style={styles.editBtn}
                >
                  Edit
                </button>
                {!brand.is_default && (
                  <button
                    onClick={() => handleDelete(brand)}
                    style={styles.deleteBtn}
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && brands.length === 0 && (
        <div style={styles.empty}>No brand kits yet. Create one to get started.</div>
      )}
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  page: {
    maxWidth: '800px',
    animation: 'fadeInUp 0.3s ease',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '24px',
  },
  title: {
    fontFamily: 'var(--font-display)',
    fontSize: '32px',
    color: 'var(--pr-charcoal)',
  },
  subtitle: {
    fontSize: '14px',
    color: 'var(--pr-gray)',
    marginTop: '2px',
  },
  addBtn: {
    padding: '10px 20px',
    borderRadius: 'var(--radius-md)',
    background: 'var(--pr-teal)',
    color: 'var(--pr-white)',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
    border: 'none',
    fontFamily: 'var(--font-body)',
  },
  formCard: {
    padding: '24px',
    borderRadius: 'var(--radius-lg)',
    background: 'var(--pr-white)',
    border: '1px solid var(--pr-beige)',
    boxShadow: 'var(--shadow-md)',
    marginBottom: '24px',
  },
  formTitle: {
    fontFamily: 'var(--font-display)',
    fontSize: '18px',
    color: 'var(--pr-charcoal)',
    marginBottom: '16px',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
    gap: '14px',
  },
  cardWrapper: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  cardActions: {
    display: 'flex',
    gap: '6px',
  },
  editBtn: {
    flex: 1,
    padding: '6px 12px',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--pr-beige)',
    background: 'var(--pr-cream)',
    fontSize: '12px',
    fontWeight: 500,
    color: 'var(--pr-charcoal)',
    cursor: 'pointer',
  },
  deleteBtn: {
    padding: '6px 12px',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid rgba(194, 59, 34, 0.3)',
    background: 'rgba(194, 59, 34, 0.06)',
    fontSize: '12px',
    fontWeight: 500,
    color: 'var(--pr-error)',
    cursor: 'pointer',
  },
  loading: {
    padding: '48px 0',
    textAlign: 'center',
    color: 'var(--pr-gray)',
  },
  empty: {
    padding: '48px 0',
    textAlign: 'center',
    color: 'var(--pr-gray)',
    fontSize: '14px',
  },
};
