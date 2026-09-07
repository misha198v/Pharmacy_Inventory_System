import { render, screen } from '@testing-library/react';
import App from './App';

test('renders the pharmacy login screen', () => {
  render(<App />);
  expect(screen.getByText(/pharmacy system/i)).toBeInTheDocument();
});
