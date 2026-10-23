import React, { useCallback, useEffect, useState } from 'react';
import {
  createUser,
  getUsers,
  resetUserPassword,
  setUserActive,
} from '../../services/sales.service';
import { formatApiError } from '../../utils/apiError';
import '../Common/Panels.css';
import '../Common/PanelsExtra.css';

const EMPTY = { username: '', password: '', role: 'staff' };

export default function UsersPanel({ currentUsername }) {
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [form, setForm] = useState(EMPTY);
  const [showPassword, setShowPassword] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [resetId, setResetId] = useState(null);
  const [newPassword, setNewPassword] = useState('');

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await getUsers();
      setUsers(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      setError(formatApiError(err, 'Could not load the users.'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      await createUser({
        username: form.username.trim(),
        password: form.password,
        role: form.role,
      });
      setNotice(
        `Created the ${form.role} account "${form.username.trim()}". Give them the password privately.`
      );
      setForm(EMPTY);
      load();
    } catch (err) {
      setError(formatApiError(err, 'Could not create the user.'));
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggleActive = async (u) => {
    const verb = u.is_active ? 'Deactivate' : 'Reactivate';
    const ok = window.confirm(
      u.is_active
        ? `Deactivate ${u.username}? They will be signed out and cannot log in until you reactivate them.`
        : `Reactivate ${u.username}?`
    );
    if (!ok) return;

    setError('');
    setNotice('');
    try {
      await setUserActive(u.id, !u.is_active);
      setNotice(`${verb}d ${u.username}.`);
      load();
    } catch (err) {
      setError(formatApiError(err, `Could not ${verb.toLowerCase()} this user.`));
    }
  };

  const handleSaveReset = async (u) => {
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      await resetUserPassword(u.id, newPassword);
      setNotice(`Password updated for ${u.username}. Give it to them privately.`);
      setResetId(null);
      setNewPassword('');
    } catch (err) {
      setError(formatApiError(err, 'Could not update the password.'));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <section className="pn-card">
      <h2 className="pn-title">Users</h2>
      <p className="pn-sub">
        Create accounts for your team and choose what each person can do. Staff can sell and add
        stock. Managers can also order, write off, and manage users.
      </p>

      <form onSubmit={handleCreate}>
        <div className="pn-form-grid">
          <div className="pn-field">
            <label htmlFor="user-name">Username</label>
            <input
              id="user-name"
              name="username"
              autoComplete="off"
              value={form.username}
              onChange={handleChange}
              disabled={isSaving}
              required
            />
          </div>
          <div className="pn-field">
            <label htmlFor="user-password">Password</label>
            <input
              id="user-password"
              name="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              value={form.password}
              onChange={handleChange}
              disabled={isSaving}
              required
            />
          </div>
          <div className="pn-field">
            <label htmlFor="user-role">Role</label>
            <select
              id="user-role"
              name="role"
              className="pn-select"
              value={form.role}
              onChange={handleChange}
              disabled={isSaving}
            >
              <option value="staff">Staff</option>
              <option value="manager">Manager</option>
            </select>
          </div>
        </div>

        <label className="pn-check">
          <input
            type="checkbox"
            checked={showPassword}
            onChange={(e) => setShowPassword(e.target.checked)}
          />
          Show password
        </label>

        <div className="pn-form-actions">
          <button type="submit" className="pn-btn" disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Create user'}
          </button>
        </div>
      </form>

      {error && (
        <div className="pn-alert" role="alert">
          {error}
        </div>
      )}
      {notice && <div className="pn-success">{notice}</div>}

      <div className="pn-scroll" style={{ marginTop: '1.25rem' }}>
        <table className="pn-table">
          <thead>
            <tr>
              <th>Username</th>
              <th>Role</th>
              <th>Status</th>
              <th>Last login</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => {
              const isYou = u.username === currentUsername;
              return (
                <React.Fragment key={u.id}>
                  <tr>
                    <td>
                      {u.username}
                      {isYou ? ' (you)' : ''}
                    </td>
                    <td>{u.role === 'manager' ? 'Manager' : 'Staff'}</td>
                    <td>
                      <span className={`pn-badge ${u.is_active ? 'pn-badge-OK' : 'pn-badge-INACTIVE'}`}>
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>{u.last_login ? new Date(u.last_login).toLocaleString() : 'Never'}</td>
                    <td>
                      <div className="pn-row-actions">
                        <button
                          className="pn-btn pn-btn-small pn-btn-ghost"
                          style={{ marginLeft: 0 }}
                          onClick={() => {
                            setResetId(u.id);
                            setNewPassword('');
                            setError('');
                            setNotice('');
                          }}
                        >
                          Reset password
                        </button>
                        {!isYou && (
                          <button
                            className={`pn-btn pn-btn-small ${
                              u.is_active ? 'pn-btn-danger' : 'pn-btn-ghost'
                            }`}
                            style={{ marginLeft: 0 }}
                            onClick={() => handleToggleActive(u)}
                          >
                            {u.is_active ? 'Deactivate' : 'Reactivate'}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                  {resetId === u.id && (
                    <tr>
                      <td colSpan="5">
                        <div className="pn-inline">
                          <div className="pn-field">
                            <label htmlFor={`reset-${u.id}`}>New password for {u.username}</label>
                            <input
                              id={`reset-${u.id}`}
                              type={showPassword ? 'text' : 'password'}
                              autoComplete="new-password"
                              value={newPassword}
                              onChange={(e) => setNewPassword(e.target.value)}
                              disabled={isSaving}
                            />
                          </div>
                          <button
                            className="pn-btn pn-btn-small"
                            onClick={() => handleSaveReset(u)}
                            disabled={isSaving || !newPassword}
                          >
                            {isSaving ? 'Saving...' : 'Save password'}
                          </button>
                          <button
                            className="pn-btn pn-btn-small pn-btn-ghost"
                            onClick={() => setResetId(null)}
                            disabled={isSaving}
                          >
                            Cancel
                          </button>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
            {!isLoading && users.length === 0 && (
              <tr>
                <td colSpan="5">No users yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
