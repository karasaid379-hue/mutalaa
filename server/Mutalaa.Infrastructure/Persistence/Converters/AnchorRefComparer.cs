using Microsoft.EntityFrameworkCore.ChangeTracking;
using Mutalaa.Domain.Anchors;

namespace Mutalaa.Infrastructure.Persistence.Converters;

/// <summary>AnchorRef degismez (record) oldugu icin Equals tabanli karsilastirici; anlik kopya ayni nesnedir.</summary>
public sealed class AnchorRefComparer()
    : ValueComparer<AnchorRef>((a, b) => a == b, a => a.GetHashCode(), a => a);
