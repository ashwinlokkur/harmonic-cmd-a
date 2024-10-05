import React, { useEffect, useState } from 'react';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogContentText,
    DialogActions,
    Button,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    CircularProgress,
} from '@mui/material';
import { getCollectionsMetadata, ICollection } from '../utils/jam-api';

interface TransferDialogProps {
    open: boolean;
    onClose: () => void;
    onTransfer: (targetCollectionId: string) => void;
    sourceCollectionId: string;
}

const TransferDialog: React.FC<TransferDialogProps> = ({
    open,
    onClose,
    onTransfer,
    sourceCollectionId,
}) => {
    const [collections, setCollections] = useState<ICollection[]>([]);
    const [selectedCollectionId, setSelectedCollectionId] = useState<string>('');
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (open) {
            setLoading(true);
            getCollectionsMetadata()
                .then((data) => {
                    const filtered = data.filter((col) => col.id !== sourceCollectionId);
                    setCollections(filtered);
                    if (filtered.length > 0) {
                        setSelectedCollectionId(filtered[0].id);
                    }
                })
                .catch(() => {
                    setError('Failed to fetch collections.');
                })
                .finally(() => {
                    setLoading(false);
                });
        }
    }, [open, sourceCollectionId]);

    const handleTransfer = () => {
        onTransfer(selectedCollectionId);
    };

    return (
        <Dialog
            open={open}
            onClose={onClose}
            aria-labelledby="transfer-dialog-title"
            aria-describedby="transfer-dialog-description"
        >
            <DialogTitle id="transfer-dialog-title">Move Companies</DialogTitle>
            <DialogContent>
                <DialogContentText id="transfer-dialog-description">
                    Select the target collection to move the selected companies to.
                </DialogContentText>
                {loading ? (
                    <CircularProgress style={{ marginTop: 20 }} />
                ) : error ? (
                    <p style={{ color: 'red' }}>{error}</p>
                ) : (
                    <FormControl fullWidth style={{ marginTop: 20 }}>
                        <InputLabel id="target-collection-label">Target Collection</InputLabel>
                        <Select
                            labelId="target-collection-label"
                            value={selectedCollectionId}
                            label="Target Collection"
                            onChange={(e) => setSelectedCollectionId(e.target.value)}
                        >
                            {collections.map((collection) => (
                                <MenuItem key={collection.id} value={collection.id}>
                                    {collection.collection_name}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                )}
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose} color="primary">
                    Cancel
                </Button>
                <Button
                    onClick={handleTransfer}
                    color="secondary"
                    disabled={loading || !selectedCollectionId}
                >
                    Move
                </Button>
            </DialogActions>
        </Dialog>
    );
};

export default TransferDialog;
