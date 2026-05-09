import type { Metadata } from "next";
import 'bootstrap/dist/css/bootstrap.min.css';
import { Container } from "react-bootstrap";

export const metadata: Metadata = {
  title: 'Тестовое задание Fullstack',
  description: 'Тестовое задание Fullstack',
};

// Favicon is auto-detected by Next from app/favicon.ico or public/favicon.ico;
// no explicit <link rel="icon"> needed (the previous /public/... path was a
// 404 anyway because public assets are served from the root, and basePath
// further rewrites it).

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body>
        <Container fluid className="p-0">
          {children}
        </Container>
      </body>
    </html>
  );
}
