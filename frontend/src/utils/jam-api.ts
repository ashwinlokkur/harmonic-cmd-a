import axios, { AxiosInstance } from 'axios';

export interface ICompany {
    id: number;
    company_name: string;
    liked: boolean;
}

export interface ICollection {
    id: string;
    collection_name: string;
    companies: ICompany[];
    total: number;
}

export interface ICompanyBatchResponse {
    companies: ICompany[];
    total: number;
}

export interface IOperationStatus {
    operation_id: string;
    operation_type?: string; // e.g., "transfer", "bulk_delete"
    status: string; // e.g., "in_progress", "completed", "failed"
    detail?: string;
}

const BASE_URL = 'http://localhost:8000';

const axiosInstance: AxiosInstance = axios.create({
    baseURL: BASE_URL,
    // Uncomment the following line if using HTTP-only cookies for authentication
    // withCredentials: true,
});

axiosInstance.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('authToken');
        if (token && config.headers) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

export async function getCompanies(offset?: number, limit?: number): Promise<ICompanyBatchResponse> {
    try {
        const response = await axiosInstance.get('/companies', {
            params: {
                offset,
                limit,
            },
        });
        return response.data;
    } catch (error) {
        console.error('Error fetching companies:', error);
        throw error;
    }
}

export async function getCollectionsById(id: string, offset?: number, limit?: number): Promise<ICollection> {
    try {
        const response = await axiosInstance.get(`/collections/${id}`, {
            params: {
                offset,
                limit,
            },
        });
        return response.data;
    } catch (error) {
        console.error('Error fetching collection by ID:', error);
        throw error;
    }
}

export async function getCollectionsMetadata(): Promise<ICollection[]> {
    try {
        const response = await axiosInstance.get('/collections');
        return response.data;
    } catch (error) {
        console.error('Error fetching collections metadata:', error);
        throw error;
    }
}

export async function bulkDeleteCompanies(collectionId: string, companyIds: number[] = []): Promise<IOperationStatus> {
    try {
        const response = await axiosInstance.delete(`/collections/${collectionId}/companies`, {
            data: {
                company_ids: companyIds,
            },
        });
        return response.data;
    } catch (error) {
        console.error('Error bulk deleting companies:', error);
        throw error;
    }
}

export async function transferCompanies(
    sourceCollectionId: string,
    targetCollectionId: string,
    companyIds: number[] = []
): Promise<IOperationStatus> {
    try {
        console.log("transfers api", sourceCollectionId, '->',targetCollectionId, ':', companyIds)
        const response = await axiosInstance.post('/transfers', {
            source_collection_id: sourceCollectionId,
            target_collection_id: targetCollectionId,
            company_ids: companyIds,
        });
        return response.data;
    } catch (error) {
        console.error('Error transferring companies:', error);
        throw error;
    }
}

export async function getOperationStatus(operationId: string): Promise<IOperationStatus> {
    try {
        const response = await axiosInstance.get(`/operations/${operationId}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching operation status:', error);
        throw error;
    }
}
