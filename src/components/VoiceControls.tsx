
import React from 'react';
import { useBrainState, StateManager } from '../brain/StateManager';
import { AssistantState } from '../brain/types';
import { brain } from '../brain/JarvisBrain';
import { AlertCircle, CheckCircle, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';

export function VoiceControls() {
    const { currentState, data } = useBrainState();

    // Permission Dialog
    const isPermissionRequired = currentState === AssistantState.PERMISSION_REQUIRED;

    // Handler for permission
    const handlePermission = (approved: boolean) => {
        brain.respondToPermission(approved);
    };

    if (!isPermissionRequired) return null;

    return (
        <Dialog open={isPermissionRequired}>
            <DialogContent className="sm:max-w-[425px] border-amber-500/50 bg-black/90 text-white">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 text-amber-500">
                        <AlertCircle className="w-5 h-5" />
                        System Permission Required
                    </DialogTitle>
                    <DialogDescription className="text-gray-300">
                        The assistant needs your permission to execute a command.
                    </DialogDescription>
                </DialogHeader>

                {data.permission && (
                    <div className="py-4 space-y-4">
                        <div className="bg-gray-800/50 p-3 rounded-lg border border-gray-700">
                            <h4 className="text-sm font-medium text-gray-400 mb-1">Command</h4>
                            <p className="text-lg font-mono text-white">{data.permission.command_summary}</p>
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-400">Operation:</span>
                                <span className="font-mono text-xs text-gray-300 truncate max-w-[200px]" title={data.permission.exact_operation}>
                                    {data.permission.exact_operation}
                                </span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-400">Risk Level:</span>
                                <span className={`uppercase font-bold text-xs ${data.permission.risk_level === 'high' ? 'text-red-500' : 'text-yellow-500'
                                    }`}>
                                    {data.permission.risk_level}
                                </span>
                            </div>
                        </div>
                    </div>
                )}

                <DialogFooter className="flex gap-2 sm:justify-between">
                    <Button
                        variant="ghost"
                        onClick={() => handlePermission(false)}
                        className="text-red-400 hover:text-red-300 hover:bg-red-900/20"
                    >
                        <XCircle className="mr-2 w-4 h-4" />
                        Deny
                    </Button>
                    <Button
                        onClick={() => handlePermission(true)}
                        className="bg-amber-600 hover:bg-amber-700 text-white"
                    >
                        <CheckCircle className="mr-2 w-4 h-4" />
                        Approve
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
