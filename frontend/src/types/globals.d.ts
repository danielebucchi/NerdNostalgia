// Declaration committata per le side-effect import di file CSS
// (es. `import "./globals.css"`).
//
// next-env.d.ts copre lo stesso caso ma e' gitignored e viene rigenerato
// solo durante `next build`/`next dev`. La CI esegue `tsc --noEmit`
// senza prima un build, quindi il file non c'e' e TS lamenta TS2882.
// Mettendolo qui sotto src/ rende la type-check riproducibile.
declare module "*.css";
declare module "*.scss";
declare module "*.sass";
declare module "*.module.css" {
  const classes: { readonly [key: string]: string };
  export default classes;
}
