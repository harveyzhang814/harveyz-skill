function slugify(s) {
  return String(s).toLowerCase().trim().replace(/\s+/g, '-');
}
if (require.main === module) {
  const cases = [
    ['Hello World', 'hello-world'],
    ['Hello, World!', 'hello-world'],
  ];
  let fail = 0;
  for (const [inp, exp] of cases) {
    const got = slugify(inp);
    const ok = got === exp;
    if (!ok) fail++;
    console.log(`${ok ? 'PASS' : 'FAIL'}  slugify(${JSON.stringify(inp)}) => ${JSON.stringify(got)} (expect ${JSON.stringify(exp)})`);
  }
  process.exit(fail ? 1 : 0);
}
module.exports = { slugify };
