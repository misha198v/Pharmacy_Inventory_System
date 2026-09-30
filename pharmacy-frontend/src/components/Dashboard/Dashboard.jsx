import React, { useState, useEffect } from 'react';
import { inventoryService } from '../../services/inventory.service';

export default function Dashboard() {
  const [medicines, setMedicines] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  // Fetch medicines on mount
  useEffect(() => {
    inventoryService.getMedicines()
      .then(res => {
        setMedicines(res.data);
        setLoading(false);
      })
      .catch(err => console.error("Error fetching inventory:", err));
  }, []);

  // 1. Low-Stock Alert calculation (Threshold = 20)
  const lowStockItems = inventoryService.checkLowStock(medicines, 20);

  // 2. Filtered and Sorted data based on search and expiry options
  const displayedMedicines = inventoryService.filterMedicines(medicines, searchQuery);

  const handleSortByExpiry = () => {
    const sorted = inventoryService.sortByExpiry(medicines);
    setMedicines([...sorted]);
  };

  if (loading) return <div className="p-6">Loading inventory...</div>;

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Pharmacy Inventory Dashboard</h1>

      {/* Feature 1: Low-Stock Warning Banner */}
      {lowStockItems.length > 0 && (
        <div className="bg-amber-100 border-l-4 border-amber-500 text-amber-800 p-4 mb-6 rounded shadow-sm">
          <p className="font-semibold">⚠️ Low Stock Alert!</p>
          <p className="text-sm">{lowStockItems.length} item(s) have fallen below the 20-unit threshold and need reordering.</p>
        </div>
      )}

      {/* Feature 3: Quick Search Bar */}
      <div className="flex flex-col md:flex-row gap-4 mb-6 justify-between items-center">
        <input 
          type="text"
          placeholder="Search by description or batch number..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="border border-gray-300 p-2 rounded w-full md:w-1/2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        {/* Feature 2: Expiry Sorting Button */}
        <button 
          onClick={handleSortByExpiry}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-medium transition"
        >
          Sort by Nearest Expiry
        </button>
      </div>

      {/* Inventory Table */}
      <div className="overflow-x-auto bg-white rounded shadow p-4">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-100 border-b text-gray-700">
              <th className="p-3">Batch Number</th>
              <th className="p-3">Description</th>
              <th className="p-3">Quantity</th>
              <th className="p-3">Days Until Expiry</th>
              <th className="p-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {displayedMedicines.length > 0 ? (
              displayedMedicines.map((item) => (
                <tr key={item.id || item.batch_number} className="border-b hover:bg-gray-50">
                  <td className="p-3 font-mono text-sm">{item.batch_number}</td>
                  <td className="p-3">{item.description}</td>
                  <td className={`p-3 font-semibold ${item.quantity < 20 ? 'text-amber-600' : 'text-gray-900'}`}>
                    {item.quantity}
                  </td>
                  <td className="p-3">{item.days_until_expiry} days</td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${
                      item.status === 'OK' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {item.status}
                    </span>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="5" className="p-6 text-center text-gray-500">
                  No matching medicines found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}