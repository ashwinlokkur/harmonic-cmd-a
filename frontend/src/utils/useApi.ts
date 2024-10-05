import { useEffect, useState } from 'react';

function useApi<T>(fetchFunction: () => Promise<T>) {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<any>(null);

    useEffect(() => {
        let isMounted = true;
        setLoading(true);
        fetchFunction()
            .then((response) => {
                if (isMounted) {
                    setData(response);
                }
            })
            .catch((err) => {
                if (isMounted) {
                    setError(err);
                }
            })
            .finally(() => {
                if (isMounted) {
                    setLoading(false);
                }
            });

        return () => {
            isMounted = false;
        };
    }, [fetchFunction]);

    return { data, loading, error };
}

export default useApi;
