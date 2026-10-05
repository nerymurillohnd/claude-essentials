<script>
  export let data;
  import { page } from '$app/stores';
</script>

<h1>{$page.params.id}</h1>
<div class="bio">{@html data.bio}</div>
