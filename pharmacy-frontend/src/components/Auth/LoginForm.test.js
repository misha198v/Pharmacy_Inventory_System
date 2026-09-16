import { render, screen, fireEvent } from '@testing-library/react';
import LoginForm from './LoginForm';

describe('LoginForm', () => {
  test('renders username and password inputs', () => {
    render(<LoginForm onSubmit={() => {}} isLoading={false} error="" />);
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  test('submits form with username and password', () => {
    const handleSubmit = jest.fn();
    render(<LoginForm onSubmit={handleSubmit} isLoading={false} error="" />);
    
    fireEvent.change(screen.getByLabelText(/username/i), { target: { value: 'testuser' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'password123' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    expect(handleSubmit).toHaveBeenCalledWith({
      username: 'testuser',
      password: 'password123',
    });
  });

  test('displays error message', () => {
    render(<LoginForm onSubmit={() => {}} isLoading={false} error="Invalid credentials" />);
    expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
  });
});