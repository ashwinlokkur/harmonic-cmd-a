import { DataGrid, GridSelectionModel, GridPaginationModel } from "@mui/x-data-grid";
import { useEffect, useState } from "react";
import {
    getCollectionsById,
    ICompany,
    transferCompanies,
    getOperationStatus,
} from "../utils/jam-api";
import Button from "@mui/material/Button";
import { useSnackbar } from 'notistack';
import CircularProgress from '@mui/material/CircularProgress';
import TransferDialog from './TransferDialog';

interface CompanyTableProps {
    selectedCollectionId: string;
}

const CompanyTable: React.FC<CompanyTableProps> = ({ selectedCollectionId }) => {
    const [companies, setCompanies] = useState<ICompany[]>([]);
    const [total, setTotal] = useState<number>(0);
    const [offset, setOffset] = useState<number>(0);
    const [pageSize, setPageSize] = useState<number>(25);
    const [pageNumber, setPageNumbeer] = useState<number>(0);
    const [selectionModel, setSelectionModel] = useState<GridSelectionModel>([]);
    const { enqueueSnackbar } = useSnackbar();
    const [loadingOperation, setLoadingOperation] = useState<boolean>(false);
    const [transferDialogOpen, setTransferDialogOpen] = useState<boolean>(false);

    useEffect(() => {
        fetchCompanies();
        // reset selection when collection changes
        setSelectionModel([]);
    }, [selectedCollectionId, offset, pageSize]);

    const fetchCompanies = async () => {
        try {
            const response = await getCollectionsById(selectedCollectionId, offset, pageSize);
            setCompanies(response.companies);
            setTotal(response.total);
        } catch (error) {
            enqueueSnackbar('Failed to fetch companies.', { variant: 'error' });
        }
    };

    const handleTransferClick = () => {
        if (selectionModel.length === 0) {
            enqueueSnackbar('No companies selected for transfer.', { variant: 'warning' });
            return;
        }
        setTransferDialogOpen(true);
    };

    const handleTransfer = async (targetCollectionId: string) => {
        setTransferDialogOpen(false);
        setLoadingOperation(true);
        try {
            const companyIds = selectionModel.map((rowId) => {
                const parts = rowId.toString().split('-');
                return parseInt(parts[parts.length - 1], 10);
            });
            const operationStatus = await transferCompanies(
                selectedCollectionId,
                targetCollectionId,
                companyIds
            );
            enqueueSnackbar(`Transfer started. Operation ID: ${operationStatus.operation_id}`, { variant: 'info' });
            
            pollOperationStatus(operationStatus.operation_id);
        } catch (error) {
            enqueueSnackbar('Failed to initiate transfer.', { variant: 'error' });
        } finally {
            setLoadingOperation(false);
        }
    };

    const pollOperationStatus = async (operationId: string) => {
        const interval = setInterval(async () => {
            try {
                const status = await getOperationStatus(operationId);
                if (status.status === 'completed') {
                    enqueueSnackbar('Transfer completed successfully.', { variant: 'success' });
                    clearInterval(interval);
                    fetchCompanies();
                    setSelectionModel([]);
                } else if (status.status === 'failed') {
                    enqueueSnackbar(`Transfer failed: ${status.detail}`, { variant: 'error' });
                    clearInterval(interval);
                } else {
                    enqueueSnackbar(`Transfer in progress... (${status.detail})`, { variant: 'info', autoHideDuration: 2000 });
                }
            } catch (error) {
                enqueueSnackbar('Error fetching operation status.', { variant: 'error' });
                clearInterval(interval);
            }
        }, 3000); // TODO: change poll from 3s
    };

    return (
        <div style={{ height: 800, width: "100%" }}>
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
                <div>
                <Button
                  variant="contained"
                  color="primary"
                  onClick={handleTransferClick}
                  disabled={selectionModel.length === 0 || loadingOperation}
                  style={{ marginRight: 8 }}
                  >
                        Move Selected ({selectionModel.length})
                    </Button>
                    {loadingOperation && <CircularProgress size={24} style={{ marginLeft: 16 }} />}
                </div>
                <div>
                    <span>Total Companies: {total}</span>
                </div>
            </div>
            <DataGrid
                rows={companies}
                rowHeight={30}
                columns={[
                    { field: "liked", headerName: "Liked", width: 90 },
                    { field: "id", headerName: "ID", width: 90 },
                    { field: "company_name", headerName: "Company Name", width: 200 },
                ]}
                getRowId={(row) => `${selectedCollectionId}-${row.id}`}
                pagination
                checkboxSelection
                paginationMode="server"
                rowCount={total}
                paginationModel={{pageSize: pageSize, page: pageNumber}}
                onPaginationModelChange={(model: GridPaginationModel) => {
                  console.log("onPaginationModelChange", model)
                  setPageSize(model.pageSize)
                  setPageNumbeer(model.page)
                  setOffset(model.page * model.pageSize)
                }}
                rowSelectionModel={selectionModel}
                onRowSelectionModelChange={(newSelection) => {
                    setSelectionModel(newSelection);
                }}
                loading={!companies.length && !loadingOperation}
            />
            <TransferDialog
                open={transferDialogOpen}
                onClose={() => setTransferDialogOpen(false)}
                onTransfer={handleTransfer}
                sourceCollectionId={selectedCollectionId}
            />
        </div>
    );

};

export default CompanyTable;
