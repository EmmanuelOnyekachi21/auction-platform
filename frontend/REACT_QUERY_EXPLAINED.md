# React Query Explained (For Your Wallet App)

## What is React Query?

React Query is a library that manages **server data** (data from APIs) in your React app. It's like a smart cache that automatically handles fetching, caching, and updating data.

## Why Use It?

**Without React Query:**
```javascript
// You have to manually manage everything
const [wallet, setWallet] = useState(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState(null);

useEffect(() => {
  fetch('/api/v1/wallets/me')
    .then(res => res.json())
    .then(data => setWallet(data))
    .catch(err => setError(err))
    .finally(() => setLoading(false));
}, []);

// Problem: How do you refetch? How do you cache? How do you sync across components?
```

**With React Query:**
```javascript
// React Query handles everything automatically
const { data: wallet, isLoading, error } = useQuery({
  queryKey: ['wallet'],
  queryFn: walletActions.getWallet,
});

// That's it! Loading, errors, caching, refetching all handled.
```

## Key Concepts in Your App

### 1. QueryClient (The Brain)

Located in `App.jsx`:
```javascript
const queryClient = new QueryClient();

<QueryClientProvider client={queryClient}>
  {/* All components inside can now use React Query */}
</QueryClientProvider>
```

Think of it as a **global cache manager** for all your API data.

### 2. useQuery (Fetch & Cache Data)

Used in `WalletPage.jsx`:
```javascript
const { data: wallet, isLoading, refetch } = useQuery({
  queryKey: ['wallet'],              // Unique ID for this data
  queryFn: walletActions.getWallet,  // Function that fetches data
  staleTime: 30_000,                 // Data is "fresh" for 30 seconds
  refetchOnWindowFocus: true,        // Refetch when user returns to tab
});
```

**What happens:**
1. First time: Fetches data from API
2. Stores it in cache with key `['wallet']`
3. Next time: Returns cached data (if still fresh)
4. After 30 seconds: Marks as "stale" and refetches in background

### 3. useMutation (Modify Data)

Used in `WalletPage.jsx` for funding:
```javascript
const mutation = useMutation({
  mutationFn: (amt) => walletActions.fundWallet(amt),
  onSuccess: (data) => {
    // After successful funding, redirect to payment
    window.location.href = data.payment_link;
  },
});

// Trigger it:
mutation.mutate(100); // Fund ₦100
```

### 4. invalidateQueries (Mark Data as Stale)

This is the **magic** that fixes your balance update issue:

```javascript
// Tell React Query: "wallet data is old, refetch it"
queryClient.invalidateQueries({ queryKey: ['wallet'] });
```

**When you call this:**
- React Query marks `['wallet']` cache as stale
- Any component using `useQuery(['wallet'])` will automatically refetch
- UI updates with fresh data

## How It Fixes Your Problem

### Before (Balance Not Updating):
```
User pays on Flutterwave
    ↓
Returns to PaymentConfirmPage
    ↓
Clicks "View Wallet"
    ↓
WalletPage shows OLD cached balance ❌
(React Query thinks data is still fresh)
```

### After (Balance Updates):
```
User pays on Flutterwave
    ↓
Returns to PaymentConfirmPage
    ↓
PaymentConfirmPage calls:
  queryClient.invalidateQueries({ queryKey: ['wallet'] })
    ↓
Clicks "View Wallet"
    ↓
WalletPage automatically refetches ✅
Shows NEW balance
```

## The Code Change

**In `PaymentConfirmPage.jsx`:**

```javascript
import { useQueryClient } from '@tanstack/react-query';

const PaymentConfirmPage = () => {
  const queryClient = useQueryClient(); // Get the cache manager

  useEffect(() => {
    setTimeout(() => {
      if (urlStatus === 'successful') {
        // Mark wallet data as stale
        queryClient.invalidateQueries({ queryKey: ['wallet'] });
      }
    }, 2500);
  }, [searchParams, queryClient]);
}
```

## Common React Query Patterns in Your App

### Pattern 1: Fetch Data
```javascript
const { data, isLoading, error } = useQuery({
  queryKey: ['wallet'],
  queryFn: walletActions.getWallet,
});
```

### Pattern 2: Mutate Data + Refetch
```javascript
const mutation = useMutation({
  mutationFn: walletActions.withdrawFunds,
  onSuccess: () => {
    // Refetch wallet to show new balance
    queryClient.invalidateQueries({ queryKey: ['wallet'] });
  },
});
```

### Pattern 3: Manual Refetch
```javascript
const { refetch } = useQuery({
  queryKey: ['wallet'],
  queryFn: walletActions.getWallet,
});

// User clicks refresh button
<button onClick={() => refetch()}>Refresh</button>
```

## Benefits You're Getting

1. **Automatic Caching** - No duplicate API calls
2. **Loading States** - `isLoading` handled automatically
3. **Error Handling** - `error` object provided
4. **Background Refetching** - Keeps data fresh
5. **Optimistic Updates** - UI updates before API responds
6. **Deduplication** - Multiple components can share same query

## Learn More

- Official Docs: https://tanstack.com/query/latest
- Your setup is already good! Just understand these 4 concepts:
  1. `QueryClient` - The cache manager
  2. `useQuery` - Fetch data
  3. `useMutation` - Change data
  4. `invalidateQueries` - Mark data as stale
