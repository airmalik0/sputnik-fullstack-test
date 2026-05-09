import type { Metadata } from "next";
import "bootstrap/dist/css/bootstrap.min.css";
import { Container } from "react-bootstrap";

import { Providers } from "@/app/providers";

export const metadata: Metadata = {
  title: "Тестовое задание Fullstack",
  description: "Тестовое задание Fullstack",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body>
        <Providers>
          <Container fluid className="p-0">
            {children}
          </Container>
        </Providers>
      </body>
    </html>
  );
}
