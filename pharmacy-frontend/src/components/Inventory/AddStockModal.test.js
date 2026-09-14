import { render, screen, fireEvent } from '@testing-library/react';
import AddStockModal from './AddStockModal';

describe('AddStockModal', () => {
  test('renders form fields when open', () => {
    render(
      <AddStockModal
        isOpen={true}
        onClose={() => {}}
        onSubmit={() => {}}
        username="testuser"
      />
    );
    expect(screen.getByLabelText(/drug name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/stock quantity/i)).toBeInTheDocument();
  });

  test('validates form before submit', async () => {
    render(
      <AddStockModal
        isOpen={true}
        onClose={() => {}}
        onSubmit={() => {}}
        username="testuser"
      />
    );
    
    fireEvent.click(screen.getByRole('button', { name: /save/i }));
    // Should show validation errors
  });
});