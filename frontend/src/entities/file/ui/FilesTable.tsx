/**
 * Files table — the read view of the files entity.
 *
 * Pure presentational component: takes data, renders rows. No data
 * fetching, no state. Loading and error are surfaced via props so the
 * page-level composition decides what to render around the table.
 */

"use client";

import { Badge, Button, Card, Spinner, Table } from "react-bootstrap";

import type { FileItem } from "@/entities/file/types";
import { filesApi } from "@/entities/file/api";
import { formatDate, formatSize } from "@/shared/lib/format";
import { ProcessingBadge, ScanBadge } from "@/shared/ui/StatusBadge";

type Props = {
  files: FileItem[];
  isLoading: boolean;
};

export function FilesTable({ files, isLoading }: Props) {
  return (
    <Card className="shadow-sm border-0 mb-4">
      <Card.Header className="bg-white border-0 pt-4 px-4">
        <div className="d-flex justify-content-between align-items-center">
          <h2 className="h5 mb-0">Файлы</h2>
          <Badge bg="secondary">{files.length}</Badge>
        </div>
      </Card.Header>
      <Card.Body className="px-4 pb-4">
        {isLoading ? (
          <div className="d-flex justify-content-center py-5">
            <Spinner animation="border" />
          </div>
        ) : (
          <div className="table-responsive">
            <Table hover bordered className="align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th>Название</th>
                  <th>Файл</th>
                  <th>MIME</th>
                  <th>Размер</th>
                  <th>Статус</th>
                  <th>Проверка</th>
                  <th>Создан</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {files.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-4 text-secondary">
                      Файлы пока не загружены
                    </td>
                  </tr>
                ) : (
                  files.map((file) => <FileRow key={file.id} file={file} />)
                )}
              </tbody>
            </Table>
          </div>
        )}
      </Card.Body>
    </Card>
  );
}

function FileRow({ file }: { file: FileItem }) {
  return (
    <tr>
      <td>
        <div className="fw-semibold">{file.title}</div>
        <div className="small text-secondary">{file.id}</div>
      </td>
      <td>{file.original_name}</td>
      <td>{file.mime_type}</td>
      <td>{formatSize(file.size)}</td>
      <td>
        <ProcessingBadge status={file.processing_status} />
      </td>
      <td>
        <div className="d-flex flex-column gap-1">
          <ScanBadge
            status={file.scan_status}
            requiresAttention={file.requires_attention}
          />
          <span className="small text-secondary">
            {file.scan_details ?? "Ожидает обработки"}
          </span>
        </div>
      </td>
      <td>{formatDate(file.created_at)}</td>
      <td className="text-nowrap">
        <Button
          as="a"
          href={filesApi.downloadUrl(file.id)}
          variant="outline-primary"
          size="sm"
        >
          Скачать
        </Button>
      </td>
    </tr>
  );
}
