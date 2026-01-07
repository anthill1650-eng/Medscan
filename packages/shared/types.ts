export interface DocPage {
  id: string;
  uri: string;
  width: number;
  height: number;
}

export interface UploadRes {
  docId: string;
  pages: DocPage[];
}
